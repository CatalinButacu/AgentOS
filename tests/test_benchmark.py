from agentos.benchmark import run_benchmark
from agentos.domain.compliance import ComplianceQuestion, Requirement
from agentos.domain.sources import Source, SourceKind
from agentos.identity.principal import Principal
from agentos.identity.roles import Role


def test_frugality_reduces_tokens_at_parity():
    question = ComplianceQuestion(
        "b", "",
        [
            Requirement("r1", "Personal data is retained no longer than 24 months."),
            Requirement("r2", "Data deletion requests are honored within 30 days."),
        ],
        [Source("s1", SourceKind.PLAIN_TEXT, "samples/policy_manual.md")],
    )
    result = run_benchmark(question, Principal("o", {Role.OWNER}))
    assert result["frugal_tokens"] < result["baseline_tokens"]
    assert result["reduction"] > 0.3
    assert result["quality_parity"] is True
