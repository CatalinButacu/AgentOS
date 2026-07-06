from agentos.config import ComplianceConfig
from agentos.domain.compliance import ComplianceQuestion, Requirement
from agentos.domain.sources import Sensitivity, Source, SourceKind
from agentos.engine import build_engine
from agentos.identity.access import AccessPolicy
from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.security.classification import SensitivityClassifier
from agentos.security.policy import PolicyGuard


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


def test_default_config_reproduces_builtin_behaviour():
    classifier = SensitivityClassifier()
    assert classifier.classify("personal data on file") == Sensitivity.CONFIDENTIAL
    assert PolicyGuard().groundedness_threshold == 0.7


def test_custom_sensitivity_rules_apply():
    classifier = SensitivityClassifier(rules=((Sensitivity.RESTRICTED, ("trade secret",)),))
    assert classifier.classify("this is a trade secret") == Sensitivity.RESTRICTED
    assert classifier.classify("personal data") == Sensitivity.INTERNAL


def test_custom_threshold_changes_escalation():
    assert PolicyGuard(groundedness_threshold=0.9).requires_human_review(0.8)
    assert not PolicyGuard(groundedness_threshold=0.5).requires_human_review(0.8)


def test_custom_clearances_change_access():
    strict = AccessPolicy()
    generous = AccessPolicy(clearances={Role.CLERK: Sensitivity.RESTRICTED})
    clerk = Principal("c", {Role.CLERK})
    assert not strict.may_access(clerk, Sensitivity.CONFIDENTIAL)
    assert generous.may_access(clerk, Sensitivity.CONFIDENTIAL)


def test_arbitrary_string_roles_need_no_enum():
    policy = AccessPolicy(clearances={"facility_manager": Sensitivity.RESTRICTED})
    manager = Principal("u", {"facility_manager"})
    stranger = Principal("s", {"visitor"})
    assert policy.may_access(manager, Sensitivity.CONFIDENTIAL)
    assert not policy.may_access(stranger, Sensitivity.CONFIDENTIAL)


def test_config_changes_outcome_without_code_change():
    default_clerk = _verdicts(build_engine().run(_question(), Principal("c", {Role.CLERK})))
    generous = ComplianceConfig(role_clearances={Role.CLERK: Sensitivity.RESTRICTED})
    lifted_clerk = _verdicts(build_engine(config=generous).run(_question(), Principal("c", {Role.CLERK})))
    assert default_clerk["r1"] != "satisfied"
    assert lifted_clerk["r1"] == "satisfied"
