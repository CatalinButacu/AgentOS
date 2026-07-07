from __future__ import annotations

import re

from agentos.agents.base import Agent
from agentos.domain.compliance import (RANGE_OPERATORS, CheckOperator, Claim,
                                       ExecutableCheck, SupportLink, Verdict)
from agentos.domain.sources import EvidenceSpan

_NUMBER_PATTERN = r"(\d+(?:\.\d+)?)"


class SandboxExecutorAgent(Agent):
    def execute_for_ground_truth(self, claim: Claim,
                                 evidence: list[EvidenceSpan]) -> SupportLink:
        check = claim.check
        if check is None or (check.operator in RANGE_OPERATORS and check.upper is None):
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        measurement = self._measure(check.unit, evidence)
        if measurement is None:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        measured_value, span_id = measurement
        verdict = Verdict.SATISFIED if _evaluate(check, measured_value) else Verdict.NOT_SATISFIED
        return SupportLink(claim.id, [span_id], verdict, 1.0)

    def _measure(self, unit: str, evidence: list[EvidenceSpan]) -> tuple[float, str] | None:
        pattern = re.compile(_NUMBER_PATTERN + r"\s*" + re.escape(unit), re.IGNORECASE)
        for span in evidence:
            match = pattern.search(span.text)
            if match:
                return float(match.group(1)), span.id
        return None


def _evaluate(check: ExecutableCheck, value: float) -> bool:
    threshold = check.threshold
    if check.operator == CheckOperator.AT_MOST:
        return value <= threshold
    if check.operator == CheckOperator.AT_LEAST:
        return value >= threshold
    if check.operator == CheckOperator.EQUALS:
        return value == threshold
    if check.operator == CheckOperator.NOT_EQUALS:
        return value != threshold
    if check.operator == CheckOperator.LESS_THAN:
        return value < threshold
    if check.operator == CheckOperator.GREATER_THAN:
        return value > threshold
    if check.operator == CheckOperator.BETWEEN:
        return threshold <= value <= check.upper
    if check.operator == CheckOperator.OUTSIDE:
        return value < threshold or value > check.upper
    return False
