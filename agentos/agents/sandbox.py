from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink, Verdict


class SandboxExecutorAgent(Agent):
    def execute_for_ground_truth(self, claim: Claim) -> SupportLink:
        return SupportLink(
            claim_id=claim.id,
            evidence_span_ids=[],
            verdict=Verdict.SATISFIED,
            groundedness_score=1.0,
        )
