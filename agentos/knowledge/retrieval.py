from __future__ import annotations

from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.knowledge.lexical import tokenize

SEMANTIC_RECALL = 5


class GraphRAGRetriever:
    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def retrieve(self, query_text: str, token_budget: int,
                 query_vector: list[float] | None = None) -> list[str]:
        scores = self.graph.search(tokenize(query_text))
        ranked_seeds = sorted(scores, key=lambda span_id: scores[span_id], reverse=True)
        if query_vector is not None:
            ranked_seeds.extend(self._semantic_recall(scores, query_vector))

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

    def _semantic_recall(self, lexical_scores: dict[str, float],
                         query_vector: list[float]) -> list[str]:
        semantic = self.graph.semantic_search(query_vector)
        ranked = sorted(semantic, key=lambda span_id: semantic[span_id], reverse=True)
        return [span_id for span_id in ranked if span_id not in lexical_scores][:SEMANTIC_RECALL]

    def _seed_with_context(self, seed: str) -> list[str]:
        ordered = [seed]
        parent = self.graph.parent_of(seed)
        if parent and self.graph.is_span(parent):
            ordered.append(parent)
        return ordered
