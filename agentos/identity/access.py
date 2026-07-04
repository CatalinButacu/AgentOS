from __future__ import annotations

from agentos.domain.sources import Sensitivity
from agentos.identity.principal import Principal
from agentos.identity.roles import ROLE_CLEARANCE, SENSITIVITY_RANK


class AccessPolicy:
    def clearance(self, principal: Principal) -> Sensitivity:
        return max((ROLE_CLEARANCE[role] for role in principal.roles),
                   key=lambda sensitivity: SENSITIVITY_RANK[sensitivity],
                   default=Sensitivity.PUBLIC)

    def may_access(self, principal: Principal, sensitivity: Sensitivity,
                   tenant_id: str | None = None) -> bool:
        if not self._tenant_ok(principal, tenant_id):
            return False
        return SENSITIVITY_RANK[sensitivity] <= SENSITIVITY_RANK[self.clearance(principal)]

    @staticmethod
    def _tenant_ok(principal: Principal, tenant_id: str | None) -> bool:
        if tenant_id is None:
            return True
        return principal.tenant_id == tenant_id
