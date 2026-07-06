from __future__ import annotations

import re

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink
from agentos.domain.sources import EvidenceSpan
from agentos.knowledge.lexical import has_negation, tokenize

CONTRADICTION_PENALTY = 0.5
_SCORE_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


class JudgeAgent(Agent):
    def __init__(self, name, models, tools,
                 contradiction_penalty: float = CONTRADICTION_PENALTY) -> None:
        super().__init__(name, models, tools)
        self.contradiction_penalty = contradiction_penalty

    def score_groundedness(self, claim: Claim, support: SupportLink,
                           evidence: list[EvidenceSpan]) -> float:
        cited = [span for span in evidence if span.id in set(support.evidence_span_ids)]
        if not cited:
            return 0.0
        if self.models.is_live:
            llm_score = self._score_with_llm(claim, cited)
            if llm_score is not None:
                return llm_score
        return self._score_deterministic(claim, cited)

    def _score_with_llm(self, claim: Claim, cited: list[EvidenceSpan]) -> float | None:
        raw = self.models.complete(_build_judge_prompt(claim, cited), difficulty="standard")
        return _parse_score(raw)

    def _score_deterministic(self, claim: Claim, cited: list[EvidenceSpan]) -> float:
        claim_terms = set(tokenize(claim.text))
        if not claim_terms:
            return 0.0
        evidence_terms: set[str] = set()
        for span in cited:
            evidence_terms |= set(tokenize(span.text))
        entailment = len(claim_terms & evidence_terms) / len(claim_terms)
        contradiction = has_negation(claim.text) != _any_negation(cited)
        penalty = self.contradiction_penalty if contradiction else 0.0
        return round(max(0.0, entailment - penalty), 3)


def _build_judge_prompt(claim: Claim, cited: list[EvidenceSpan]) -> str:
    evidence_block = "\n".join(f"- {span.text}" for span in cited)
    return (
        "Rate how well the evidence supports the claim on a scale from 0 to 1, "
        "where 1 means fully supported and 0 means unsupported or contradicted. "
        "Reply with only the number.\n\n"
        f"Claim: {claim.text}\n\nEvidence:\n{evidence_block}"
    )


def _parse_score(raw: str) -> float | None:
    if not raw:
        return None
    match = _SCORE_PATTERN.search(raw)
    if not match:
        return None
    try:
        value = float(match.group(0))
    except ValueError:
        return None
    return round(max(0.0, min(1.0, value)), 3)


def _any_negation(spans: list[EvidenceSpan]) -> bool:
    return any(has_negation(span.text) for span in spans)
