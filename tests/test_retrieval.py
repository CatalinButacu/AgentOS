from agentos.ingestion.chunker import Chunker
from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.knowledge.retrieval import FullContextRetriever, GraphRAGRetriever

DOCUMENT = "# Retention\n\nData retained for 24 months.\n\n# Access\n\nBadge access required."


def _graph():
    graph = EvidenceGraph()
    graph.add_document("doc.s", "uri")
    spans = Chunker().chunk("doc.s", "s", "1", DOCUMENT)
    for span in spans:
        graph.add_span(span, "doc.s")
    return graph, spans


def test_retriever_returns_relevant_span():
    graph, spans = _graph()
    retained = next(span for span in spans if "retained" in span.text)
    result = GraphRAGRetriever(graph).retrieve("data retained months", token_budget=2000)
    assert retained.id in result


def test_full_context_returns_everything():
    graph, spans = _graph()
    result = FullContextRetriever(graph).retrieve("anything", token_budget=1)
    assert set(result) == {span.id for span in spans}


def test_graphrag_is_smaller_than_full_context():
    graph, _ = _graph()
    frugal = GraphRAGRetriever(graph).retrieve("data retained months", token_budget=2000)
    full = FullContextRetriever(graph).retrieve("data retained months", token_budget=2000)
    assert len(frugal) <= len(full)
