from __future__ import annotations

from agentos.infra.observability import Observability


class AzureMonitorExporter:
    def __init__(self, connection_string: str | None = None) -> None:
        self.connection_string = connection_string

    @classmethod
    def from_env(cls) -> "AzureMonitorExporter":
        from agentos.settings import Settings
        return cls.from_settings(Settings.from_env())

    @classmethod
    def from_settings(cls, settings) -> "AzureMonitorExporter":
        return cls(settings.app_insights_connection_string)

    @property
    def is_live(self) -> bool:
        return bool(self.connection_string)

    def export(self, observability: Observability, trace_name: str = "compliance.run") -> int | None:
        if not self.is_live:
            return None
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        except ImportError as error:
            raise RuntimeError(
                "azure-monitor-opentelemetry-exporter and opentelemetry-sdk are required "
                "for a live AzureMonitorExporter") from error

        provider = TracerProvider(resource=Resource.create({"service.name": "agentos"}))
        provider.add_span_processor(
            SimpleSpanProcessor(AzureMonitorTraceExporter(connection_string=self.connection_string)))
        tracer = provider.get_tracer(trace_name)

        exported = 0
        for span in observability.spans:
            otel_span = tracer.start_span(
                span.name, start_time=int(span.started_at.timestamp() * 1_000_000_000))
            for key, value in span.attributes.items():
                otel_span.set_attribute(key, _attribute_value(value))
            otel_span.set_attribute("status", span.status)
            otel_span.end(end_time=int(span.ended_at.timestamp() * 1_000_000_000))
            exported += 1
        provider.force_flush()
        return exported


def _attribute_value(value):
    if isinstance(value, (str, bool, int, float)):
        return value
    return str(value)
