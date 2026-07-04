from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Span:
    name: str
    attributes: dict
    duration_ms: float
    status: str


class SpanRecorder:
    def __init__(self, attributes: dict) -> None:
        self.attributes = dict(attributes)

    def set(self, key: str, value) -> None:
        self.attributes[key] = value

    def set_all(self, attributes: dict) -> None:
        self.attributes.update(attributes)


class Observability:
    def __init__(self, echo: bool = False) -> None:
        self.echo = echo
        self.spans: list[Span] = []

    @contextmanager
    def span(self, name: str, **attributes):
        started = time.perf_counter()
        recorder = SpanRecorder(attributes)
        status = "ok"
        try:
            yield recorder
        except Exception:
            status = "error"
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            completed = Span(name, recorder.attributes, duration_ms, status)
            self.spans.append(completed)
            if self.echo:
                rendered = " ".join(f"{key}={value}" for key, value in completed.attributes.items())
                print(f"[span] {name} {duration_ms}ms {rendered}")

    def record(self, span_name: str, payload: dict) -> None:
        with self.span(span_name) as recorder:
            recorder.set_all(payload)

    def sum_attribute(self, key: str) -> float:
        return sum(span.attributes.get(key, 0) for span in self.spans)

    def duration_of(self, name: str) -> float:
        return round(sum(span.duration_ms for span in self.spans if span.name == name), 3)
