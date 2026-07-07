from __future__ import annotations

import re

from agentos.agents.base import Agent
from agentos.domain.compliance import (RANGE_OPERATORS, CheckOperator, Claim,
                                       ExecutableCheck, SupportLink, Verdict)
from agentos.domain.sources import EvidenceSpan
from agentos.infra.tool_gateway import Tool

_NUMBER_PATTERN = r"(\d+(?:\.\d+)?)"


def measure_metric(unit: str, evidence: list[EvidenceSpan]) -> tuple[float, str] | None:
    pattern = re.compile(_NUMBER_PATTERN + r"\s*" + re.escape(unit), re.IGNORECASE)
    for span in evidence:
        match = pattern.search(span.text)
        if match:
            return float(match.group(1)), span.id
    return None


class SandboxExecutorAgent(Agent):
    def __init__(self, name, models, tools) -> None:
        super().__init__(name, models, tools)
        self.register_tools(tools)

    def register_tools(self, gateway) -> None:
        gateway.register(Tool("measure_metric",
                              "Measure a numeric value in the given unit from evidence spans",
                              measure_metric, ("unit", "evidence")))

    def execute_for_ground_truth(self, claim: Claim, evidence: list[EvidenceSpan],
                                 gateway=None) -> SupportLink:
        gateway = gateway or self.tools
        check = claim.check
        if check is None or (check.operator in RANGE_OPERATORS and check.upper is None):
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        call = gateway.call("measure_metric", {"unit": check.unit, "evidence": evidence})
        measurement = call.result if call.ok else None
        if measurement is None:
            return SupportLink(claim.id, [], Verdict.INSUFFICIENT_EVIDENCE, 0.0)
        measured_value, span_id = measurement
        verdict = Verdict.SATISFIED if _evaluate(check, measured_value) else Verdict.NOT_SATISFIED
        return SupportLink(claim.id, [span_id], verdict, 1.0)


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
