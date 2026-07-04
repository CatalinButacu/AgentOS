from __future__ import annotations

from typing import Callable

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink, Verdict
from agentos.domain.sources import EvidenceSpan
from agentos.knowledge.lexical import tokenize

SUPPORT_THRESHOLD = 0.6


class VerifierAgent(Agent):
    def verify(self, claim: Claim, evidence: list[EvidenceSpan]) -> SupportLink:
        claim_terms = set(tokenize(claim.text))
        if not claim_terms or not evidence:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        support = self._assess(claim.id, claim_terms, evidence, _strict_match)
        if support.groundedness_score < SUPPORT_THRESHOLD:
            support = self.reflect_and_retry(claim, support, evidence)
        return support

    def reflect_and_retry(self, claim: Claim, weak_support: SupportLink,
                          evidence: list[EvidenceSpan]) -> SupportLink:
        claim_terms = set(tokenize(claim.text))
        relaxed = self._assess(claim.id, claim_terms, evidence, _relaxed_match)
        if relaxed.groundedness_score > weak_support.groundedness_score:
            return relaxed
        return weak_support

    def _assess(self, claim_id: str, claim_terms: set[str],
                evidence: list[EvidenceSpan],
                matches: Callable[[str, set[str]], bool]) -> SupportLink:
        supporting_span_ids: list[str] = []
        covered_terms: set[str] = set()
        for span in evidence:
            span_terms = set(tokenize(span.text))
            hits = {term for term in claim_terms if matches(term, span_terms)}
            if hits:
                supporting_span_ids.append(span.id)
                covered_terms |= hits
        if not supporting_span_ids:
            return SupportLink(claim_id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        coverage = round(len(covered_terms) / len(claim_terms), 3)
        verdict = Verdict.SATISFIED if coverage >= SUPPORT_THRESHOLD else Verdict.INSUFFICIENT_EVIDENCE
        return SupportLink(claim_id, supporting_span_ids, verdict, coverage)


def _strict_match(term: str, span_terms: set[str]) -> bool:
    return term in span_terms


def _relaxed_match(term: str, span_terms: set[str]) -> bool:
    if term in span_terms:
        return True
    prefix = term[:4]
    return any(len(other) >= 4 and other[:4] == prefix for other in span_terms)
