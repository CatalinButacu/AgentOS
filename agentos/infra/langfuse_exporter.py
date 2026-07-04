from __future__ import annotations

import os

from agentos.infra.observability import Observability, Span


def to_observations(spans: list[Span]) -> list[dict]:
    return [{
        "name": span.name,
        "metadata": span.attributes,
        "status": span.status,
        "duration_ms": span.duration_ms,
        "start_time": span.started_at,
        "end_time": span.ended_at,
    } for span in spans]


class LangfuseExporter:
    def __init__(self, public_key: str | None = None, secret_key: str | None = None,
                 host: str | None = None) -> None:
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host or "https://cloud.langfuse.com"

    @classmethod
    def from_env(cls) -> "LangfuseExporter":
        return cls(public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                   secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                   host=os.environ.get("LANGFUSE_HOST"))

    @property
    def is_live(self) -> bool:
        return bool(self.public_key and self.secret_key)

    def export(self, observability: Observability,
               trace_name: str = "compliance.run") -> str | None:
        observations = to_observations(observability.spans)
        if not self.is_live:
            return None
        try:
            from langfuse import Langfuse
        except ImportError as error:
            raise RuntimeError("langfuse is required for a live LangfuseExporter") from error
        client = Langfuse(public_key=self.public_key, secret_key=self.secret_key, host=self.host)
        trace = client.trace(name=trace_name)
        for observation in observations:
            trace.span(name=observation["name"],
                       metadata=observation["metadata"],
                       start_time=observation["start_time"],
                       end_time=observation["end_time"],
                       status_message=observation["status"])
        client.flush()
        return trace.id
