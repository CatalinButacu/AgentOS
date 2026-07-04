from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim


class RetrieverAgent(Agent):
    def gather_evidence(self, claim: Claim, token_budget: int) -> list[str]:
        return []
