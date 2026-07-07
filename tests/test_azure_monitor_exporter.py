from agentos.infra.azure_monitor_exporter import AzureMonitorExporter
from agentos.infra.observability import Observability
from agentos.settings import Settings


def test_not_live_without_connection_string():
    assert not AzureMonitorExporter(None).is_live
    assert AzureMonitorExporter.from_settings(Settings.from_env({})).is_live is False


def test_live_with_connection_string():
    settings = Settings.from_env({"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=abc"})
    assert AzureMonitorExporter.from_settings(settings).is_live


def test_export_is_noop_when_offline():
    observability = Observability()
    with observability.span("compliance.run", question_id="q"):
        pass
    assert AzureMonitorExporter(None).export(observability) is None
