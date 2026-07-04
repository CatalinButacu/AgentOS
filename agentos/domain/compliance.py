from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from agentos.domain.sources import Source


class Verdict(Enum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ESCALATED_TO_HUMAN = "escalated_to_human"


@dataclass
class Requirement:
    id: str
    text: str


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


@dataclass
class ComplianceReport:
    question_id: str
    findings: list[Finding]
    generated_at: datetime
