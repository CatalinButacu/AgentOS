from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from agentos.domain.sources import Source


class Verdict(Enum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ESCALATED_TO_HUMAN = "escalated_to_human"


class CheckOperator(Enum):
    AT_MOST = "at_most"
    AT_LEAST = "at_least"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    BETWEEN = "between"
    OUTSIDE = "outside"


RANGE_OPERATORS = frozenset({CheckOperator.BETWEEN, CheckOperator.OUTSIDE})


@dataclass
class ExecutableCheck:
    metric: str
    unit: str
    operator: CheckOperator
    threshold: float
    upper: float | None = None


@dataclass
class Requirement:
    id: str
    text: str
    check: ExecutableCheck | None = None


@dataclass
class ComplianceQuestion:
    id: str
    text: str
    requirements: list[Requirement]
    sources: list[Source]


@dataclass
class Claim:
    id: str
    requirement_id: str
    text: str
    is_executable: bool = False
    check: ExecutableCheck | None = None


@dataclass
class SupportLink:
    claim_id: str
    evidence_span_ids: list[str]
    verdict: Verdict
    groundedness_score: float


@dataclass
class Finding:
    requirement_id: str
    claim_id: str
    verdict: Verdict
    groundedness_score: float
    supporting_span_ids: list[str]
    escalated_to_human: bool
    tool_trace: list[dict] = field(default_factory=list)


@dataclass
class ComplianceReport:
    question_id: str
    findings: list[Finding]
    generated_at: datetime
