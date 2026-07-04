from __future__ import annotations

from agentos.domain.compliance import SupportLink
from agentos.domain.graph import GraphEdge, GraphNode


class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes_by_id: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.support_links: list[SupportLink] = []

    def add_node(self, node: GraphNode) -> GraphNode:
        self.nodes_by_id[node.id] = node
        return node

    def link(self, source_id: str, target_id: str, kind: str) -> GraphEdge:
        edge = GraphEdge(source_id, target_id, kind)
        self.edges.append(edge)
        return edge

    def record_support(self, support: SupportLink) -> None:
        self.support_links.append(support)

    def provenance_subgraph(self, requirement_id: str) -> "EvidenceGraph":
        return EvidenceGraph()

    def expand(self, node_id: str) -> "EvidenceGraph":
        return EvidenceGraph()
