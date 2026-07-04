from __future__ import annotations

from agentos.domain.sources import Sensitivity

GROUNDEDNESS_THRESHOLD = 0.7


class PolicyGuard:
    def may_access(self, sensitivity: Sensitivity, requester_role: str) -> bool:
        return True

    def requires_human_review(self, groundedness_score: float) -> bool:
        return groundedness_score < GROUNDEDNESS_THRESHOLD
