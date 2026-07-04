from __future__ import annotations

import os
import re
from dataclasses import dataclass

from agentos.domain.sources import BoundingBox, ElementType, Source

_HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.*\S)\s*$")
_PARAGRAPH_SEPARATOR = re.compile(r"\n\s*\n")


@dataclass
class ExtractedElement:
    text: str
    element_type: ElementType
    char_start: int
    char_end: int
    page_number: int | None = None
    bounding_box: BoundingBox | None = None
    heading_level: int | None = None


@dataclass
class ExtractionResult:
    text: str
    elements: list[ExtractedElement]
    page_count: int
    extraction_method: str


def structural_elements(text: str) -> list[ExtractedElement]:
    elements: list[ExtractedElement] = []
    cursor = 0
    for block in _PARAGRAPH_SEPARATOR.split(text):
        block_start = text.find(block, cursor)
        cursor = block_start + len(block)
        stripped = block.strip()
        if not stripped:
            continue
        heading = _HEADING_PATTERN.match(stripped)
        if heading:
            elements.append(ExtractedElement(
                text=heading.group(2),
                element_type=ElementType.HEADING,
                char_start=block_start,
                char_end=cursor,
                heading_level=len(heading.group(1)),
            ))
        else:
            elements.append(ExtractedElement(
                text=stripped,
                element_type=ElementType.PARAGRAPH,
                char_start=block_start,
                char_end=cursor,
            ))
    return elements


class TextExtractor:
    def extract(self, source: Source) -> ExtractionResult:
        raise NotImplementedError


class PlainTextExtractor(TextExtractor):
    def extract(self, source: Source) -> ExtractionResult:
        text = self._read(source.uri)
        return ExtractionResult(text=text, elements=structural_elements(text),
                                page_count=1, extraction_method="plain_text")

    @staticmethod
    def _read(uri: str) -> str:
        path = uri[7:] if uri.startswith("file://") else uri
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return ""


def _role_to_element(role: str | None) -> tuple[ElementType, int | None]:
    if role == "title":
        return ElementType.HEADING, 1
    if role == "sectionHeading":
        return ElementType.HEADING, 2
    return ElementType.PARAGRAPH, None


def _polygon_to_box(region) -> BoundingBox | None:
    polygon = list(getattr(region, "polygon", None) or [])
    horizontal = polygon[0::2]
    vertical = polygon[1::2]
    if not horizontal or not vertical:
        return None
    left = min(horizontal)
    top = min(vertical)
    return BoundingBox(page=region.page_number, x=left, y=top,
                       width=max(horizontal) - left, height=max(vertical) - top)


class AzureDocumentIntelligenceExtractor(TextExtractor):
    def __init__(self, endpoint: str, key: str, model_id: str = "prebuilt-layout") -> None:
        self.endpoint = endpoint
        self.key = key
        self.model_id = model_id
        self._client = None

    @classmethod
    def from_env(cls, model_id: str = "prebuilt-layout") -> "AzureDocumentIntelligenceExtractor":
        return cls(os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"],
                   os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"], model_id)

    def _client_or_create(self):
        if self._client is None:
            try:
                from azure.ai.documentintelligence import DocumentIntelligenceClient
                from azure.core.credentials import AzureKeyCredential
            except ImportError as error:
                raise RuntimeError(
                    "azure-ai-documentintelligence and azure-core are required for "
                    "AzureDocumentIntelligenceExtractor") from error
            self._client = DocumentIntelligenceClient(self.endpoint, AzureKeyCredential(self.key))
        return self._client

    def extract(self, source: Source) -> ExtractionResult:
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        client = self._client_or_create()
        if source.uri.startswith("http://") or source.uri.startswith("https://"):
            poller = client.begin_analyze_document(
                self.model_id, AnalyzeDocumentRequest(url_source=source.uri))
        else:
            path = source.uri[7:] if source.uri.startswith("file://") else source.uri
            with open(path, "rb") as handle:
                poller = client.begin_analyze_document(
                    self.model_id, handle, content_type="application/octet-stream")
        result = poller.result()
        elements = self._map_paragraphs(result)
        page_count = len(result.pages) if getattr(result, "pages", None) else 1
        return ExtractionResult(text=result.content or "", elements=elements,
                                page_count=page_count,
                                extraction_method=f"azure:{self.model_id}")

    def _map_paragraphs(self, result) -> list[ExtractedElement]:
        elements: list[ExtractedElement] = []
        for paragraph in getattr(result, "paragraphs", None) or []:
            element_type, heading_level = _role_to_element(getattr(paragraph, "role", None))
            regions = getattr(paragraph, "bounding_regions", None) or []
            region = regions[0] if regions else None
            spans = getattr(paragraph, "spans", None) or []
            span = spans[0] if spans else None
            char_start = span.offset if span else 0
            char_end = (span.offset + span.length) if span else 0
            elements.append(ExtractedElement(
                text=paragraph.content,
                element_type=element_type,
                char_start=char_start,
                char_end=char_end,
                page_number=region.page_number if region else None,
                bounding_box=_polygon_to_box(region) if region else None,
                heading_level=heading_level,
            ))
        return elements


if __name__ == "__main__":
    import sys
    from agentos.domain.sources import SourceKind
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/data_retention_policy.md"
    extraction = PlainTextExtractor().extract(Source("s1", SourceKind.PLAIN_TEXT, path))
    print(f"method={extraction.extraction_method} pages={extraction.page_count} "
          f"elements={len(extraction.elements)}")
    for element in extraction.elements:
        print(f"  [{element.element_type.value} lvl={element.heading_level}] {element.text[:60]}")
