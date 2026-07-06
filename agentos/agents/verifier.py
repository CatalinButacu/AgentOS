from __future__ import annotations

import json
import re
from typing import Callable

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, SupportLink, Verdict
from agentos.domain.sources import EvidenceSpan
from agentos.knowledge.lexical import tokenize

SUPPORT_THRESHOLD = 0.6
_VERDICT_BY_VALUE = {verdict.value: verdict for verdict in Verdict}


class VerifierAgent(Agent):
    def __init__(self, name, models, tools,
                 support_threshold: float = SUPPORT_THRESHOLD) -> None:
        super().__init__(name, models, tools)
        self.support_threshold = support_threshold

    def verify(self, claim: Claim, evidence: list[EvidenceSpan]) -> SupportLink:
        if self.models.is_live and evidence:
            llm_support = self._verify_with_llm(claim, evidence)
            if llm_support is not None:
                return llm_support
        return self._verify_deterministic(claim, evidence)

    def _verify_with_llm(self, claim: Claim,
                         evidence: list[EvidenceSpan]) -> SupportLink | None:
        raw = self.models.complete(_build_verify_prompt(claim, evidence), difficulty="standard")
        return _parse_support(claim, evidence, raw)

    def _verify_deterministic(self, claim: Claim,
                              evidence: list[EvidenceSpan]) -> SupportLink:
        claim_terms = set(tokenize(claim.text))
        if not claim_terms or not evidence:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        support = self._assess(claim.id, claim_terms, evidence, _strict_match)
        if support.groundedness_score < self.support_threshold:
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
        verdict = Verdict.SATISFIED if coverage >= self.support_threshold else Verdict.INSUFFICIENT_EVIDENCE
        return SupportLink(claim_id, supporting_span_ids, verdict, coverage)


def _build_verify_prompt(claim: Claim, evidence: list[EvidenceSpan]) -> str:
    evidence_block = "\n".join(f"[{span.id}] {span.text}" for span in evidence)
    return (
        "You are a compliance verifier. Decide whether the requirement is supported "
        "by the evidence, using only the evidence provided.\n\n"
        f"Requirement: {claim.text}\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        'Respond with JSON only: {"verdict": "satisfied|not_satisfied|insufficient_evidence", '
        '"supporting_span_ids": ["id"], "groundedness": 0.0}'
    )


def _parse_support(claim: Claim, evidence: list[EvidenceSpan],
                   raw: str) -> SupportLink | None:
    payload = _extract_json(raw)
    if payload is None:
        return None
    verdict = _VERDICT_BY_VALUE.get(str(payload.get("verdict")))
    if verdict is None:
        return None
    valid_ids = {span.id for span in evidence}
    supporting = [span_id for span_id in payload.get("supporting_span_ids", []) if span_id in valid_ids]
    try:
        groundedness = float(payload.get("groundedness", 0.0))
    except (TypeError, ValueError):
        return None
    return SupportLink(claim.id, supporting, verdict, round(max(0.0, min(1.0, groundedness)), 3))


def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _strict_match(term: str, span_terms: set[str]) -> bool:
    return term in span_terms


def _relaxed_match(term: str, span_terms: set[str]) -> bool:
    if term in span_terms:
        return True
    prefix = term[:4]
    return any(len(other) >= 4 and other[:4] == prefix for other in span_terms)
