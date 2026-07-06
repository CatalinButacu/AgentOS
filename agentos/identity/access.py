from __future__ import annotations

from collections.abc import Mapping

from agentos.domain.sources import Sensitivity
from agentos.identity.principal import Principal
from agentos.identity.roles import ROLE_CLEARANCE, SENSITIVITY_RANK, Role


class AccessPolicy:
    def __init__(self, clearances: Mapping[Role, Sensitivity] | None = None,
                 sensitivity_rank: Mapping[Sensitivity, int] | None = None) -> None:
        self.clearances = clearances if clearances is not None else ROLE_CLEARANCE
        self.sensitivity_rank = sensitivity_rank if sensitivity_rank is not None else SENSITIVITY_RANK

    def clearance(self, principal: Principal) -> Sensitivity:
        return max((self.clearances[role] for role in principal.roles if role in self.clearances),
                   key=lambda sensitivity: self.sensitivity_rank[sensitivity],
                   default=Sensitivity.PUBLIC)

    def may_access(self, principal: Principal, sensitivity: Sensitivity,
                   tenant_id: str | None = None) -> bool:
        if not self._tenant_ok(principal, tenant_id):
            return False
        return self.sensitivity_rank[sensitivity] <= self.sensitivity_rank[self.clearance(principal)]

    @staticmethod
    def _tenant_ok(principal: Principal, tenant_id: str | None) -> bool:
        if tenant_id is None:
            return True
        return principal.tenant_id == tenant_id
