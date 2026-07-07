from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str = "dev-key"
    db_path: str | None = None
    encryption_key: str | None = None
    key_vault_url: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str | None = None
    azure_openai_embedding_deployment: str | None = None
    azure_document_intelligence_endpoint: str | None = None
    azure_document_intelligence_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env

        def value(name: str) -> str | None:
            return env.get(name) or None

        return cls(
            api_key=env.get("AGENTOS_API_KEY", "dev-key"),
            db_path=value("AGENTOS_DB_PATH"),
            encryption_key=value("AGENTOS_ENCRYPTION_KEY"),
            key_vault_url=value("AZURE_KEY_VAULT_URL"),
            azure_openai_endpoint=value("AZURE_OPENAI_ENDPOINT"),
            azure_openai_api_key=value("AZURE_OPENAI_API_KEY"),
            azure_openai_api_version=env.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_openai_chat_deployment=value("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            azure_openai_embedding_deployment=value("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            azure_document_intelligence_endpoint=value("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            azure_document_intelligence_key=value("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
            langfuse_public_key=value("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=value("LANGFUSE_SECRET_KEY"),
            langfuse_host=value("LANGFUSE_HOST"),
        )
