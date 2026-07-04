from __future__ import annotations

import math

from agentos.domain.compliance import SupportLink
from agentos.domain.graph import GraphEdge, GraphNode
from agentos.domain.sources import EvidenceSpan
from agentos.knowledge.lexical import tokenize


class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes_by_id: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.support_links: list[SupportLink] = []
        self.postings: dict[str, set[str]] = {}
        self.token_estimate_by_id: dict[str, int] = {}
        self.parent_by_id: dict[str, str] = {}
        self.embedding_by_id: dict[str, list[float]] = {}
        self.span_ids: set[str] = set()

    def add_node(self, node: GraphNode) -> GraphNode:
        self.nodes_by_id[node.id] = node
        return node

    def link(self, source_id: str, target_id: str, kind: str) -> GraphEdge:
        edge = GraphEdge(source_id, target_id, kind)
        self.edges.append(edge)
        return edge

    def add_document(self, document_id: str, label: str) -> None:
        if document_id not in self.nodes_by_id:
            self.add_node(GraphNode(id=document_id, kind="document", zoom_level=0, label=label))

    def add_span(self, span: EvidenceSpan, document_id: str,
                 embedding: list[float] | None = None) -> None:
        meta = span.metadata
        label = "/".join(meta.section_path) or span.text[:60]
        self.add_node(GraphNode(id=span.id, kind=meta.element_type.value,
                                zoom_level=meta.zoom_level, label=label,
                                observed_at=meta.observed_at))
        self.span_ids.add(span.id)
        parent_id = meta.parent_id or document_id
        self.parent_by_id[span.id] = parent_id
        self.link(parent_id, span.id, "CONTAINS")
        self.token_estimate_by_id[span.id] = max(1, len(span.text.split()))
        for term in set(tokenize(span.text)):
            self.postings.setdefault(term, set()).add(span.id)
        if embedding is not None:
            self.embedding_by_id[span.id] = embedding

    def search(self, query_terms: list[str]) -> dict[str, float]:
        total_spans = max(1, len(self.span_ids))
        scores: dict[str, float] = {}
        for term in set(query_terms):
            matches = self.postings.get(term)
            if not matches:
                continue
            inverse_document_frequency = math.log(1 + total_spans / len(matches))
            for span_id in matches:
                scores[span_id] = scores.get(span_id, 0.0) + inverse_document_frequency
        return scores

    def semantic_search(self, query_vector: list[float]) -> dict[str, float]:
        query_norm = math.sqrt(sum(value * value for value in query_vector)) or 1.0
        scores: dict[str, float] = {}
        for span_id, vector in self.embedding_by_id.items():
            vector_norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            dot = sum(left * right for left, right in zip(query_vector, vector))
            scores[span_id] = dot / (query_norm * vector_norm)
        return scores

    def parent_of(self, span_id: str) -> str | None:
        return self.parent_by_id.get(span_id)

    def is_span(self, node_id: str) -> bool:
        return node_id in self.span_ids

    def token_estimate(self, span_id: str) -> int:
        return self.token_estimate_by_id.get(span_id, 1)

    def record_support(self, support: SupportLink) -> None:
        self.support_links.append(support)
