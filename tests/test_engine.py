from agentos.domain.compliance import ComplianceQuestion, Requirement
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
