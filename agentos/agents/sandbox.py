from __future__ import annotations

import re

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, CheckOperator, SupportLink, Verdict
from agentos.domain.sources import EvidenceSpan

_NUMBER_PATTERN = r"(\d+(?:\.\d+)?)"


class SandboxExecutorAgent(Agent):
    def execute_for_ground_truth(self, claim: Claim,
                                 evidence: list[EvidenceSpan]) -> SupportLink:
        check = claim.check
        if check is None:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        measurement = self._measure(check.unit, evidence)
        if measurement is None:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        measured_value, span_id = measurement
        satisfied = _evaluate(check.operator, measured_value, check.threshold)
        verdict = Verdict.SATISFIED if satisfied else Verdict.NOT_SATISFIED
        return SupportLink(claim.id, [span_id], verdict, 1.0)

    def _measure(self, unit: str, evidence: list[EvidenceSpan]) -> tuple[float, str] | None:
        pattern = re.compile(_NUMBER_PATTERN + r"\s*" + re.escape(unit), re.IGNORECASE)
        for span in evidence:
            match = pattern.search(span.text)
            if match:
                return float(match.group(1)), span.id
        return None


def _evaluate(operator: CheckOperator, measured_value: float, threshold: float) -> bool:
    if operator == CheckOperator.AT_MOST:
        return measured_value <= threshold
    if operator == CheckOperator.AT_LEAST:
        return measured_value >= threshold
    return measured_value == threshold
