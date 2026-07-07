from agentos.agents.judge import JudgeAgent
from agentos.agents.retriever import RetrieverAgent
from agentos.agents.sandbox import SandboxExecutorAgent
from agentos.agents.verifier import VerifierAgent
from agentos.domain.compliance import (CheckOperator, Claim, ExecutableCheck,
                                       SupportLink, Verdict)
from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import ToolGateway
from agentos.ingestion.chunker import Chunker


class _CannedModels(ModelRouter):
    def __init__(self, response):
        super().__init__(endpoint="endpoint", api_key="key")
        self.response = response

    def complete(self, prompt, difficulty="standard"):
        return self.response


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


def test_sandbox_evaluates_range():
    sandbox = SandboxExecutorAgent(*_agent_args())
    evidence = _spans("Personal data is retained for 18 months.")
    inside = Claim("c", "r", "retention", True,
                   ExecutableCheck("retention", "months", CheckOperator.BETWEEN, 12, 24))
    outside = Claim("c", "r", "retention", True,
                    ExecutableCheck("retention", "months", CheckOperator.BETWEEN, 20, 24))
    assert sandbox.execute_for_ground_truth(inside, evidence).verdict == Verdict.SATISFIED
    assert sandbox.execute_for_ground_truth(outside, evidence).verdict == Verdict.NOT_SATISFIED


def test_sandbox_new_comparators():
    sandbox = SandboxExecutorAgent(*_agent_args())
    evidence = _spans("Personal data is retained for 24 months.")
    greater = Claim("c", "r", "retention", True,
                    ExecutableCheck("retention", "months", CheckOperator.GREATER_THAN, 12))
    not_equals = Claim("c", "r", "retention", True,
                       ExecutableCheck("retention", "months", CheckOperator.NOT_EQUALS, 24))
    assert sandbox.execute_for_ground_truth(greater, evidence).verdict == Verdict.SATISFIED
    assert sandbox.execute_for_ground_truth(not_equals, evidence).verdict == Verdict.NOT_SATISFIED


def test_sandbox_range_without_upper_is_undecidable():
    sandbox = SandboxExecutorAgent(*_agent_args())
    evidence = _spans("Personal data is retained for 18 months.")
    malformed = Claim("c", "r", "retention", True,
                      ExecutableCheck("retention", "months", CheckOperator.BETWEEN, 12))
    assert sandbox.execute_for_ground_truth(malformed, evidence).verdict == Verdict.INSUFFICIENT_EVIDENCE


def test_verifier_uses_llm_when_live():
    evidence = _spans("Personal data retained for 24 months.")
    span_id = evidence[0].id
    models = _CannedModels(
        f'{{"verdict": "satisfied", "supporting_span_ids": ["{span_id}"], "groundedness": 0.9}}')
    verifier = VerifierAgent("verifier", models, ToolGateway())
    support = verifier.verify(Claim("c", "r", "retention rule"), evidence)
    assert support.verdict == Verdict.SATISFIED
    assert support.groundedness_score == 0.9
    assert span_id in support.evidence_span_ids


def test_verifier_falls_back_on_bad_llm_output():
    evidence = _spans("Personal data retained for 24 months.")
    verifier = VerifierAgent("verifier", _CannedModels("not json at all"), ToolGateway())
    support = verifier.verify(Claim("c", "r", "personal data retained months"), evidence)
    assert support.verdict == Verdict.SATISFIED


def test_judge_uses_llm_when_live():
    evidence = _spans("Personal data retained for 24 months.")
    support = SupportLink("c", [evidence[0].id], Verdict.SATISFIED, 1.0)
    judge = JudgeAgent("judge", _CannedModels("0.42"), ToolGateway())
    assert judge.score_groundedness(Claim("c", "r", "retention"), support, evidence) == 0.42


def test_sandbox_routes_through_gateway_and_logs():
    tools = ToolGateway()
    sandbox = SandboxExecutorAgent("sandbox", ModelRouter(), tools)
    evidence = _spans("Personal data is retained for 24 months.")
    claim = Claim("c", "r", "retention", True,
                  ExecutableCheck("retention", "months", CheckOperator.AT_MOST, 24))
    assert sandbox.execute_for_ground_truth(claim, evidence).verdict == Verdict.SATISFIED
    assert [call.name for call in tools.calls] == ["measure_metric"]


def test_retriever_routes_through_gateway_and_logs():
    tools = ToolGateway()

    class _FakeRetriever:
        def retrieve(self, query_text, token_budget, query_vector=None):
            return ["span.1"]

    agent = RetrieverAgent("retriever", ModelRouter(), tools, _FakeRetriever())
    assert agent.gather_evidence(Claim("c", "r", "a claim about data"), token_budget=100) == ["span.1"]
    assert [call.name for call in tools.calls] == ["retrieve_evidence"]
