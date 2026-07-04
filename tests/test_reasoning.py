from agentos.agents.judge import JudgeAgent
from agentos.agents.sandbox import SandboxExecutorAgent
from agentos.agents.verifier import VerifierAgent
from agentos.domain.compliance import (CheckOperator, Claim, ExecutableCheck,
                                       SupportLink, Verdict)
from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import ToolGateway
from agentos.ingestion.chunker import Chunker


def _agent_args():
    return ("agent", ModelRouter(), ToolGateway())


def _spans(text):
    return Chunker().chunk("doc.s", "s", "1", text)


def test_verifier_distinguishes_support():
    verifier = VerifierAgent(*_agent_args())
    claim = Claim("c", "r", "personal data retained months")
    supported = _spans("Personal data retained for 24 months.")
    unsupported = _spans("Badge access required for server rooms.")
    assert verifier.verify(claim, supported).verdict == Verdict.SATISFIED
    assert verifier.verify(claim, unsupported).verdict == Verdict.INSUFFICIENT_EVIDENCE


def test_judge_penalizes_contradiction():
    judge = JudgeAgent(*_agent_args())
    claim = Claim("c", "r", "Personal data is retained no longer than 24 months")
    aligned = _spans("Personal data is retained no longer than 24 months.")
    contradicting = _spans("Personal data is not retained under this policy.")
    aligned_support = SupportLink("c", [aligned[0].id], Verdict.SATISFIED, 1.0)
    contradicting_support = SupportLink("c", [contradicting[0].id], Verdict.SATISFIED, 1.0)
    aligned_score = judge.score_groundedness(claim, aligned_support, aligned)
    contradicting_score = judge.score_groundedness(claim, contradicting_support, contradicting)
    assert aligned_score > contradicting_score


def test_sandbox_evaluates_numeric_rule():
    sandbox = SandboxExecutorAgent(*_agent_args())
    evidence = _spans("Personal data is retained for 24 months.")
    passing = Claim("c", "r", "retention", True,
                    ExecutableCheck("retention", "months", CheckOperator.AT_MOST, 24))
    failing = Claim("c", "r", "retention", True,
                    ExecutableCheck("retention", "months", CheckOperator.AT_MOST, 12))
    assert sandbox.execute_for_ground_truth(passing, evidence).verdict == Verdict.SATISFIED
    assert sandbox.execute_for_ground_truth(failing, evidence).verdict == Verdict.NOT_SATISFIED
