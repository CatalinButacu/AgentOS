from agentos.domain.sources import ElementType
from agentos.ingestion.chunker import Chunker, content_hash
from agentos.ingestion.dedup import BloomFilter, ContentDeduper

SAMPLE = "# Policy\n\nData is retained 24 months.\n\n## Deletion\n\nHonored within 30 days."


def test_chunker_builds_hierarchy():
    spans = Chunker().chunk("doc.s", "s", "1", SAMPLE)
    kinds = {span.metadata.element_type for span in spans}
    assert ElementType.HEADING in kinds
    assert ElementType.PARAGRAPH in kinds
    paragraphs = [span for span in spans if span.metadata.element_type == ElementType.PARAGRAPH]
    assert any(paragraph.metadata.parent_id is not None for paragraph in paragraphs)


def test_chunker_is_deterministic():
    first = Chunker().chunk("doc.s", "s", "1", SAMPLE)
    second = Chunker().chunk("doc.s", "s", "1", SAMPLE)
    assert [span.id for span in first] == [span.id for span in second]


def test_content_hash_normalizes_whitespace():
    assert content_hash("a  b") == content_hash("a b")


def test_bloom_filter_has_no_false_negatives():
    bloom = BloomFilter(expected_items=100)
    for key in ("alpha", "beta", "gamma"):
        bloom.add(key)
    assert all(key in bloom for key in ("alpha", "beta", "gamma"))


def test_deduper_flags_repeats():
    deduper = ContentDeduper(BloomFilter(expected_items=100))
    assert deduper.is_new("x") is True
    assert deduper.is_new("x") is False
    assert deduper.is_new("y") is True
