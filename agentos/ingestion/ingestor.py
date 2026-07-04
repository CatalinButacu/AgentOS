from __future__ import annotations

from dataclasses import replace

from agentos.domain.sources import Document, Source
from agentos.infra.tool_gateway import ToolGateway
from agentos.ingestion.chunker import Chunker
from agentos.security.classification import SensitivityClassifier
from agentos.security.store import SecureEvidenceStore


class DocumentIngestor:
    def __init__(self, classifier: SensitivityClassifier, chunker: Chunker,
                 store: SecureEvidenceStore, tools: ToolGateway) -> None:
        self.classifier = classifier
        self.chunker = chunker
        self.store = store
        self.tools = tools

    def ingest(self, source: Source, raw_text: str = "") -> Document:
        document_id = f"doc.{source.id}"
        document_version = "1"
        spans = self.chunker.chunk(document_id, source.id, document_version, raw_text)
        stored_span_ids: list[str] = []
        for span in spans:
            classified = replace(
                span,
                metadata=replace(span.metadata,
                                 sensitivity=self.classifier.classify(span.text)),
            )
            self.store.put(classified)
            stored_span_ids.append(classified.id)
        return Document(id=document_id, source=source,
                        version=document_version, span_ids=stored_span_ids)
