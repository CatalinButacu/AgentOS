from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from agentos.domain.sources import (ElementType, EvidenceSpan, Sensitivity,
                                     SpanMetadata)
from agentos.ingestion.extraction import ExtractedElement, structural_elements

CHUNKER_NAME = "structural"
CHUNKER_VERSION = "1"


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.blake2b(normalized.encode("utf-8"), digest_size=16).hexdigest()


class Chunker:
    def __init__(self, name: str = CHUNKER_NAME, version: str = CHUNKER_VERSION) -> None:
        self.name = name
        self.version = version

    def chunk(self, document_id: str, source_id: str, document_version: str,
              text: str, extraction_method: str = "plain_text",
              default_sensitivity: Sensitivity = Sensitivity.INTERNAL,
              observed_at: datetime | None = None) -> list[EvidenceSpan]:
        return self.chunk_elements(document_id, source_id, document_version,
                                   structural_elements(text),
                                   extraction_method=extraction_method,
                                   default_sensitivity=default_sensitivity,
                                   observed_at=observed_at)

    def chunk_elements(self, document_id: str, source_id: str, document_version: str,
                       elements: list[ExtractedElement],
                       extraction_method: str = "plain_text",
                       default_sensitivity: Sensitivity = Sensitivity.INTERNAL,
                       observed_at: datetime | None = None) -> list[EvidenceSpan]:
        observed_at = observed_at or datetime.now(timezone.utc)
        spans: list[EvidenceSpan] = []
        section_path: list[str] = []
        current_section_id: str | None = None
        ordinal = 0

        for element in elements:
            stripped = element.text.strip()
            if not stripped:
                continue
            is_heading = element.element_type == ElementType.HEADING and bool(element.heading_level)
            if is_heading:
                section_path = section_path[: element.heading_level - 1] + [stripped]
                zoom_level = 1
                parent_id = None
            else:
                zoom_level = 2
                parent_id = current_section_id

            digest = content_hash(stripped)
            span_id = f"{document_id}:{ordinal:04d}:{digest[:12]}"
            metadata = SpanMetadata(
                source_id=source_id,
                document_id=document_id,
                document_version=document_version,
                content_hash=digest,
                extraction_method=extraction_method,
                chunker_name=self.name,
                chunker_version=self.version,
                element_type=element.element_type,
                ordinal=ordinal,
                zoom_level=zoom_level,
                char_start=element.char_start,
                char_end=element.char_end,
                observed_at=observed_at,
                sensitivity=default_sensitivity,
                section_path=list(section_path),
                parent_id=parent_id,
                page_number=element.page_number,
                bounding_box=element.bounding_box,
            )
            spans.append(EvidenceSpan(id=span_id, text=stripped, metadata=metadata))

            if is_heading:
                current_section_id = span_id
            ordinal += 1

        return spans


if __name__ == "__main__":
    sample = """# Data Retention Policy

Personal data is retained for no longer than 24 months.

## Deletion Requests

Data deletion requests are honored within 30 days.
"""
    for span in Chunker().chunk("doc.s1", "s1", "1", sample):
        meta = span.metadata
        print(f"[{meta.element_type.value} L{meta.zoom_level} #{meta.ordinal}] "
              f"parent={meta.parent_id} page={meta.page_number} "
              f"{'/'.join(meta.section_path)} :: {span.text[:60]}")
