from __future__ import annotations

from dataclasses import replace

from agentos.domain.sources import Document, Source
from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import ToolGateway
from agentos.ingestion.chunker import Chunker
from agentos.ingestion.extraction import TextExtractor
from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.security.classification import SensitivityClassifier
from agentos.security.store import SecureEvidenceStore


class DocumentIngestor:
    def __init__(self, classifier: SensitivityClassifier, chunker: Chunker,
                 extractor: TextExtractor, store: SecureEvidenceStore,
                 graph: EvidenceGraph, embedder: ModelRouter,
                 tools: ToolGateway) -> None:
        self.classifier = classifier
        self.chunker = chunker
        self.extractor = extractor
        self.store = store
        self.graph = graph
        self.embedder = embedder
        self.tools = tools

    def ingest(self, source: Source) -> Document:
        extraction = self.extractor.extract(source)
        document_id = f"doc.{source.id}"
        document_version = "1"
        self.graph.add_document(document_id, source.uri)
        spans = self.chunker.chunk_elements(
            document_id, source.id, document_version, extraction.elements,
            extraction_method=extraction.extraction_method)
        stored_span_ids: list[str] = []
        for span in spans:
            classified = replace(
                span,
                metadata=replace(span.metadata,
                                 sensitivity=self.classifier.classify(span.text)))
            embedding = self.embedder.embed(classified.text)
            self.graph.add_span(classified, document_id, embedding)
            self.store.put(classified)
            stored_span_ids.append(classified.id)
        return Document(id=document_id, source=source,
                        version=document_version, span_ids=stored_span_ids)
