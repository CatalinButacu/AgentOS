from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink
from agentos.domain.sources import EvidenceSpan
from agentos.knowledge.lexical import has_negation, tokenize

CONTRADICTION_PENALTY = 0.5


class JudgeAgent(Agent):
    def score_groundedness(self, claim: Claim, support: SupportLink,
                           evidence: list[EvidenceSpan]) -> float:
        cited_ids = set(support.evidence_span_ids)
        cited = [span for span in evidence if span.id in cited_ids]
        claim_terms = set(tokenize(claim.text))
        if not cited or not claim_terms:
            return 0.0
        evidence_terms: set[str] = set()
        for span in cited:
            evidence_terms |= set(tokenize(span.text))
        entailment = len(claim_terms & evidence_terms) / len(claim_terms)
        contradiction = has_negation(claim.text) != _any_negation(cited)
        penalty = CONTRADICTION_PENALTY if contradiction else 0.0
        return round(max(0.0, entailment - penalty), 3)


def _any_negation(spans: list[EvidenceSpan]) -> bool:
    return any(has_negation(span.text) for span in spans)
