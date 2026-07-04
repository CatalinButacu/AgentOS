from __future__ import annotations

from agentos.domain.sources import Document, Source
from agentos.infra.tool_gateway import ToolGateway
from agentos.security.classification import SensitivityClassifier
from agentos.security.store import SecureEvidenceStore


class DocumentIngestor:
    def __init__(self, classifier: SensitivityClassifier,
                 store: SecureEvidenceStore, tools: ToolGateway) -> None:
        self.classifier = classifier
        self.store = store
        self.tools = tools

    def ingest(self, source: Source) -> Document:
        return Document(id=f"doc.{source.id}", source=source, span_ids=[])
