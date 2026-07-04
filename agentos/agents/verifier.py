from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink, Verdict
from agentos.domain.sources import EvidenceSpan


class VerifierAgent(Agent):
    def verify(self, claim: Claim, evidence: list[EvidenceSpan]) -> SupportLink:
        return SupportLink(
            claim_id=claim.id,
            evidence_span_ids=[span.id for span in evidence],
            verdict=Verdict.INSUFFICIENT_EVIDENCE,
            groundedness_score=0.0,
        )

    def reflect_and_retry(self, claim: Claim, weak_support: SupportLink) -> SupportLink:
        return weak_support
