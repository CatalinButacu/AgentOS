from __future__ import annotations

from agentos.domain.compliance import ComplianceQuestion, Requirement
from agentos.domain.sources import Source, SourceKind
from agentos.engine import build_engine
from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.knowledge.retrieval import FullContextRetriever


def _verdicts(report) -> dict[str, str]:
    return {finding.requirement_id: finding.verdict.value for finding in report.findings}


def run_benchmark(question: ComplianceQuestion, principal: Principal) -> dict:
    frugal_engine = build_engine()
    baseline_engine = build_engine(FullContextRetriever)
    frugal_report = frugal_engine.run(question, principal)
    baseline_report = baseline_engine.run(question, principal)
    frugal_tokens = int(frugal_engine.observability.sum_attribute("evidence.tokens"))
    baseline_tokens = int(baseline_engine.observability.sum_attribute("evidence.tokens"))
    return {
        "frugal_tokens": frugal_tokens,
        "baseline_tokens": baseline_tokens,
        "reduction": round(1 - frugal_tokens / baseline_tokens, 3) if baseline_tokens else 0.0,
        "frugal_verdicts": _verdicts(frugal_report),
        "baseline_verdicts": _verdicts(baseline_report),
        "quality_parity": _verdicts(frugal_report) == _verdicts(baseline_report),
    }


if __name__ == "__main__":
    question = ComplianceQuestion(
        id="benchmark",
        text="Does the manual satisfy data-retention and deletion rules?",
        requirements=[
            Requirement("r1", "Personal data is retained no longer than 24 months."),
            Requirement("r2", "Data deletion requests are honored within 30 days."),
        ],
        sources=[Source("s1", SourceKind.PLAIN_TEXT, "samples/policy_manual.md")],
    )
    principal = Principal("u.owner", {Role.OWNER})
    result = run_benchmark(question, principal)
    print("Frugality benchmark: GraphRAG vs fat-context baseline")
    print(f"  baseline evidence tokens: {result['baseline_tokens']}")
    print(f"  frugal   evidence tokens: {result['frugal_tokens']}")
    print(f"  token reduction:          {result['reduction'] * 100:.1f}%")
    print(f"  quality parity (verdicts): {result['quality_parity']}")
    print(f"  frugal verdicts:   {result['frugal_verdicts']}")
    print(f"  baseline verdicts: {result['baseline_verdicts']}")
