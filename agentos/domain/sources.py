from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceKind(Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    REPOSITORY = "repository"
    WEBPAGE = "webpage"
    PLAIN_TEXT = "plain_text"


class Sensitivity(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class Source:
    id: str
    kind: SourceKind
    uri: str


@dataclass
class EvidenceSpan:
    id: str
    source_id: str
    locator: str
    text: str
    sensitivity: Sensitivity
    observed_at: datetime


@dataclass
class Document:
    id: str
    source: Source
    span_ids: list[str] = field(default_factory=list)
