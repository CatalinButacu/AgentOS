from agentos.domain.compliance import (CheckOperator, ComplianceQuestion,
                                       ExecutableCheck, Requirement)
from agentos.domain.sources import Source, SourceKind
from agentos.engine import build_engine
from agentos.identity.principal import Principal
from agentos.identity.roles import Role


def _question():
    return ComplianceQuestion(
        "q", "",
        [
            Requirement("r1", "Personal data is retained no longer than 24 months."),
            Requirement("r2", "Data deletion requests are honored within 30 days."),
        ],
        [Source("s1", SourceKind.PLAIN_TEXT, "samples/data_retention_policy.md")],
    )


def _verdicts(report):
    return {finding.requirement_id: finding.verdict.value for finding in report.findings}


def test_owner_satisfies_all():
    report = build_engine().run(_question(), Principal("o", {Role.OWNER}))
    verdicts = _verdicts(report)
    assert verdicts["r1"] == "satisfied"
    assert verdicts["r2"] == "satisfied"


def test_rbac_changes_outcome():
    clerk = _verdicts(build_engine().run(_question(), Principal("c", {Role.CLERK})))
    owner = _verdicts(build_engine().run(_question(), Principal("o", {Role.OWNER})))
    assert clerk["r1"] != "satisfied"
    assert owner["r1"] == "satisfied"


def test_findings_carry_per_claim_tool_trace():
    question = ComplianceQuestion(
        "q", "",
        [Requirement("r1", "Personal data is retained no longer than 24 months.",
                     ExecutableCheck("retention", "months", CheckOperator.AT_MOST, 24))],
        [Source("s1", SourceKind.PLAIN_TEXT, "samples/data_retention_policy.md")],
    )
    report = build_engine().run(question, Principal("o", {Role.OWNER}))
    tools_used = [entry["tool"] for entry in report.findings[0].tool_trace]
    assert "retrieve_evidence" in tools_used
    assert "measure_metric" in tools_used


def test_human_in_the_loop_resolves_escalation():
    def decider(payload):
        return {requirement_id: "not_satisfied" for requirement_id in payload["escalated"]}

    engine = build_engine(human_decider=decider)
    report = engine.run(_question(), Principal("c", {Role.CLERK}))
    r1 = next(finding for finding in report.findings if finding.requirement_id == "r1")
    assert r1.escalated_to_human is False
    assert r1.verdict.value == "not_satisfied"
