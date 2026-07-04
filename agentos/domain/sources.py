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


class ElementType(Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE_ROW = "table_row"
    LIST_ITEM = "list_item"
    FIGURE_CAPTION = "figure_caption"
    CODE_BLOCK = "code_block"


@dataclass
class Source:
    id: str
    kind: SourceKind
    uri: str


@dataclass
class BoundingBox:
    page: int
    x: float
    y: float
    width: float
    height: float


@dataclass
class SpanMetadata:
    source_id: str
    document_id: str
    document_version: str
    content_hash: str
    extraction_method: str
    chunker_name: str
    chunker_version: str
    element_type: ElementType
    ordinal: int
    zoom_level: int
    char_start: int
    char_end: int
    observed_at: datetime
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    section_path: list[str] = field(default_factory=list)
    parent_id: str | None = None
    page_number: int | None = None
    bounding_box: BoundingBox | None = None
    source_published_at: datetime | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    pii_categories: list[str] = field(default_factory=list)
    jurisdiction: str | None = None
    retention_policy: str | None = None
    legal_hold: bool = False
    tenant_id: str | None = None
    classification_confidence: float | None = None
    language: str | None = None
    embedding_model: str | None = None
    embedding_ref: str | None = None


@dataclass
class EvidenceSpan:
    id: str
    text: str
    metadata: SpanMetadata


@dataclass
class Document:
    id: str
    source: Source
    version: str
    span_ids: list[str] = field(default_factory=list)
