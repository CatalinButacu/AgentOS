from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Principal:
    id: str
    roles: set[str] = field(default_factory=set)
    tenant_id: str | None = None
