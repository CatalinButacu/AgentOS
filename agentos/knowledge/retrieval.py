from __future__ import annotations

from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.knowledge.lexical import tokenize


class GraphRAGRetriever:
    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def retrieve(self, query_text: str, token_budget: int) -> list[str]:
        scores = self.graph.search(tokenize(query_text))
        ranked_seeds = sorted(scores, key=lambda span_id: scores[span_id], reverse=True)
        selected: list[str] = []
        seen: set[str] = set()
        used_tokens = 0
        for seed in ranked_seeds:
            for candidate in self._seed_with_context(seed):
                if candidate in seen:
                    continue
                cost = self.graph.token_estimate(candidate)
                if selected and used_tokens + cost > token_budget:
                    return selected
                seen.add(candidate)
                selected.append(candidate)
                used_tokens += cost
        return selected

    def _seed_with_context(self, seed: str) -> list[str]:
        ordered = [seed]
        parent = self.graph.parent_of(seed)
        if parent and self.graph.is_span(parent):
            ordered.append(parent)
        return ordered
