from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GraphNode:
    id: str
    kind: str
    zoom_level: int
    label: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observed_at: datetime | None = None


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    kind: str
