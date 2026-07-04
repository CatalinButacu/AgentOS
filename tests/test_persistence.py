from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.ingestion.chunker import Chunker
from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.persistence.kv import InMemoryStore, SqliteStore
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard
from agentos.security.store import SecureEvidenceStore


def test_in_memory_store_round_trip():
    backend = InMemoryStore()
    backend.put("ns", "k", b"value")
    assert backend.get("ns", "k") == b"value"
    assert backend.get("ns", "missing") is None
    assert backend.items("ns") == [("k", b"value")]


def test_evidence_store_persists_across_instances(tmp_path):
    database = str(tmp_path / "evidence.db")
    span = Chunker().chunk("doc.s", "s", "1", "Personal data here.")[0]

    writer_backend = SqliteStore(database)
    SecureEvidenceStore(EncryptionService(), PolicyGuard(), writer_backend).put(span)
    writer_backend.close()

    reader_backend = SqliteStore(database)
    reopened = SecureEvidenceStore(EncryptionService(), PolicyGuard(), reader_backend)
    result = reopened.get_permitted([span.id], Principal("o", {Role.OWNER}))
    reader_backend.close()

    assert result
    assert result[0].text == "Personal data here."


def test_graph_saves_and_loads(tmp_path):
    database = str(tmp_path / "graph.db")
    graph = EvidenceGraph()
    graph.add_document("doc.s", "uri")
    spans = Chunker().chunk("doc.s", "s", "1", "# Retention\n\nData retained for 24 months.")
    for span in spans:
        graph.add_span(span, "doc.s")

    writer_backend = SqliteStore(database)
    graph.save(writer_backend)
    writer_backend.close()

    reader_backend = SqliteStore(database)
    restored = EvidenceGraph()
    assert restored.load(reader_backend) is True
    reader_backend.close()

    assert restored.span_ids == graph.span_ids
    assert restored.search(["retained"])
