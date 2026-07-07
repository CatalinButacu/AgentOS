import base64

from agentos.domain.compliance import ComplianceQuestion, Requirement
from agentos.domain.sources import Sensitivity, Source, SourceKind
from agentos.engine import build_engine
from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.infra.model_router import ModelRouter
from agentos.security.encryption import EncryptionService
from agentos.settings import Settings


def test_defaults_when_env_empty():
    s = Settings.from_env({})
    assert s.api_key == "dev-key"
    assert s.db_path is None
    assert s.azure_openai_endpoint is None


def test_reads_values_from_env():
    s = Settings.from_env({"AGENTOS_API_KEY": "k", "AGENTOS_DB_PATH": "x.db",
                           "AZURE_OPENAI_ENDPOINT": "https://e", "AZURE_OPENAI_API_KEY": "ak"})
    assert s.api_key == "k"
    assert s.db_path == "x.db"
    assert s.azure_openai_endpoint == "https://e"


def test_model_router_offline_without_azure_settings():
    router = ModelRouter.from_settings(Settings.from_env({}))
    assert not router.is_live
    assert router.embed("some text")


def test_model_router_live_with_azure_settings():
    s = Settings.from_env({"AZURE_OPENAI_ENDPOINT": "https://e", "AZURE_OPENAI_API_KEY": "ak"})
    assert ModelRouter.from_settings(s).is_live


def test_encryption_from_settings_uses_configured_key():
    key = base64.b64encode(b"0" * 32).decode()
    service = EncryptionService.from_settings(Settings.from_env({"AGENTOS_ENCRYPTION_KEY": key}))
    ciphertext = service.encrypt("secret text", Sensitivity.INTERNAL)
    assert service.decrypt(ciphertext, Sensitivity.INTERNAL) == "secret text"


def test_build_engine_with_settings_runs_offline():
    question = ComplianceQuestion(
        "q", "",
        [Requirement("r2", "Data deletion requests are honored within 30 days.")],
        [Source("s1", SourceKind.PLAIN_TEXT, "samples/data_retention_policy.md")],
    )
    report = build_engine(settings=Settings.from_env({})).run(question, Principal("o", {Role.OWNER}))
    assert report.findings
