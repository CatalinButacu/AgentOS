# Deploying AgentOS to Azure Container Apps

`main.bicep` provisions the full stack in one resource group:

- **Container Apps** environment + app (external ingress on port 8000, `/health` probes, HTTP scale 1–3)
- **Azure Container Registry** (image source, pulled via managed identity — no admin user)
- **User-assigned managed identity** with `AcrPull` and `Key Vault Secrets User` roles
- **Key Vault** (RBAC mode) holding the API key and the Azure service keys
- **Azure OpenAI** account with `chat` + `embedding` deployments
- **Document Intelligence** account
- **Log Analytics** workspace (Container Apps logs)
- **PostgreSQL flexible server** — optional (`deployDatabase=true`), wired in once `PostgresStore` lands

The app reads everything through the `Settings` object; secrets arrive as Key Vault–backed secret references resolved by the managed identity.

## Prerequisites

- Azure CLI (`az`) with the `containerapp` extension, logged in to the target subscription
- Your user needs **Key Vault Secrets Officer** on the vault's scope (RBAC auth is enabled, so ARM writes the secrets through the data plane)
- Azure OpenAI access approved on the subscription, and the chosen models available in `location` (adjust the `chatModel` / `embeddingModel` params per region)

## Deploy

```bash
# 1. Resource group
az group create -n agentos-rg -l swedencentral

# 2. First deployment — creates ACR, identity, Key Vault, OpenAI, env, and the app.
#    The app boots on a public placeholder image; its first revision is unhealthy until the real image exists. Expected.
az deployment group create \
  -g agentos-rg \
  -f infra/main.bicep \
  -p infra/main.parameters.json \
  -p agentosApiKey='<a-strong-key>'

# 3. Build + push the AgentOS image straight into the new ACR (no local Docker needed)
ACR=$(az deployment group show -g agentos-rg -n main --query properties.outputs.acrName.value -o tsv)
az acr build -r "$ACR" -t agentos:1 .

# 4. Point the app at the real image
az containerapp update -g agentos-rg -n agentos-api --image "$ACR.azurecr.io/agentos:1"

# 5. Get the URL
az deployment group show -g agentos-rg -n main --query properties.outputs.apiUrl.value -o tsv
```

Smoke test:

```bash
URL=$(az deployment group show -g agentos-rg -n main --query properties.outputs.apiUrl.value -o tsv)
curl "$URL/health"
```

## Deploy via GitHub Actions (optional, manual)

`.github/workflows/deploy.yml` builds and deploys the same way, but **only when you trigger it** — it is `workflow_dispatch` (manual) and never runs on push, so it can't deploy without your explicit action. It signs in with **OIDC** (no stored passwords) and runs `scripts/smoke.py` against the live app afterward.

To enable it, configure a federated credential (an app registration or user-assigned identity with rights on `agentos-rg`) and add these **repository secrets**:

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` — for the OIDC login
- `AGENTOS_API_KEY` — used by the post-deploy smoke test

Then: **Actions → deploy → Run workflow**, and enter an image tag. Adjust `RESOURCE_GROUP` / `APP_NAME` at the top of the workflow if you renamed them.

`scripts/smoke.py` also runs locally against any base URL:

```bash
SMOKE_BASE_URL=http://127.0.0.1:8000 SMOKE_API_KEY=dev-key python scripts/smoke.py
```

## Notes

- **Validate before deploying:** `az bicep build -f infra/main.bicep` compiles the template and catches API/version issues (model availability and OpenAI quota are region-specific).
- **Live vs offline:** with the OpenAI env vars set (they are, via this template), `ModelRouter.is_live` is true and the app uses Azure OpenAI; with them unset it stays offline-deterministic.
- **Postgres:** pass `-p deployDatabase=true postgresAdminPassword='<pw>'` to provision the flexible server. The app keeps using in-memory / SQLite until `PostgresStore` is implemented (Phase 3).
- CI/CD (build → push → deploy via OIDC) is the next phase; this template is what that pipeline targets.
