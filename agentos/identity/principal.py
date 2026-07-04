from __future__ import annotations

from dataclasses import dataclass, field

from agentos.identity.roles import Role


@dataclass
class Principal:
    id: str
    roles: set[Role] = field(default_factory=set)
    tenant_id: str | None = None
