@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short prefix for resource names (lowercase, 3-11 chars).')
@minLength(3)
@maxLength(11)
param namePrefix string = 'agentos'

@description('Container image the app runs. Defaults to a public placeholder so the first deploy succeeds; update to <acr>.azurecr.io/agentos:<tag> after pushing.')
param containerImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('AgentOS API key; stored in Key Vault and injected into the app.')
@secure()
param agentosApiKey string

@description('Azure OpenAI chat model and version for the "chat" deployment.')
param chatModel string = 'gpt-4o-mini'
param chatModelVersion string = '2024-07-18'

@description('Azure OpenAI embedding model and version for the "embedding" deployment.')
param embeddingModel string = 'text-embedding-3-small'
param embeddingModelVersion string = '1'

@description('Provision a PostgreSQL flexible server (used once PostgresStore lands).')
param deployDatabase bool = false

@secure()
@description('PostgreSQL administrator password (only used when deployDatabase = true).')
param postgresAdminPassword string = ''

var suffix = uniqueString(resourceGroup().id)
var acrName = toLower('${namePrefix}acr${suffix}')
var kvName = toLower('${namePrefix}kv${substring(suffix, 0, 6)}')
var openAiName = '${namePrefix}-openai-${suffix}'
var docIntelName = '${namePrefix}-docintel-${suffix}'
var logName = '${namePrefix}-logs-${suffix}'
var envName = '${namePrefix}-env-${suffix}'
var identityName = '${namePrefix}-id-${suffix}'
var appName = '${namePrefix}-api'

var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var kvSecretsUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: 'chat'
  sku: { name: 'Standard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: chatModel, version: chatModelVersion }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: 'embedding'
  dependsOn: [ chatDeployment ]
  sku: { name: 'Standard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: embeddingModel, version: embeddingModelVersion }
  }
}

resource docIntel 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: docIntelName
    publicNetworkAccess: 'Enabled'
  }
}

resource apiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'agentos-api-key'
  properties: { value: agentosApiKey }
}

resource openAiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-openai-api-key'
  properties: { value: openAi.listKeys().key1 }
}

resource docIntelKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-document-intelligence-key'
  properties: { value: docIntel.listKeys().key1 }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: acrPullRoleId
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, identity.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: kvSecretsUserRoleId
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [ acrPull, kvSecretsUser ]
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: [
        {
          name: 'agentos-api-key'
          keyVaultUrl: apiKeySecret.properties.secretUri
          identity: identity.id
        }
        {
          name: 'azure-openai-api-key'
          keyVaultUrl: openAiKeySecret.properties.secretUri
          identity: identity.id
        }
        {
          name: 'azure-document-intelligence-key'
          keyVaultUrl: docIntelKeySecret.properties.secretUri
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'agentos'
          image: containerImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'AGENTOS_API_KEY', secretRef: 'agentos-api-key' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.properties.endpoint }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-api-key' }
            { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: 'chat' }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: 'embedding' }
            { name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', value: docIntel.properties.endpoint }
            { name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY', secretRef: 'azure-document-intelligence-key' }
            { name: 'AZURE_KEY_VAULT_URL', value: keyVault.properties.vaultUri }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = if (deployDatabase) {
  name: '${namePrefix}-pg-${suffix}'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: 'agentos'
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    highAvailability: { mode: 'Disabled' }
  }
}

output apiUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output identityClientId string = identity.properties.clientId
output keyVaultName string = keyVault.name
