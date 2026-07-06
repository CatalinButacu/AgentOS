from __future__ import annotations

from agentos.domain.sources import Sensitivity
from agentos.identity.access import AccessPolicy
from agentos.identity.principal import Principal

GROUNDEDNESS_THRESHOLD = 0.7


class PolicyGuard:
    def __init__(self, access_policy: AccessPolicy | None = None,
                 groundedness_threshold: float = GROUNDEDNESS_THRESHOLD) -> None:
        self.access_policy = access_policy or AccessPolicy()
        self.groundedness_threshold = groundedness_threshold

    def may_access(self, principal: Principal, sensitivity: Sensitivity,
                   tenant_id: str | None = None) -> bool:
        return self.access_policy.may_access(principal, sensitivity, tenant_id)

    def requires_human_review(self, groundedness_score: float) -> bool:
        return groundedness_score < self.groundedness_threshold
