from __future__ import annotations

from datetime import datetime

from agentos.agents.judge import JudgeAgent
from agentos.agents.planner import Planner
from agentos.agents.retriever import RetrieverAgent
from agentos.agents.sandbox import SandboxExecutorAgent
from agentos.agents.verifier import VerifierAgent
from agentos.domain.compliance import (CheckOperator, ComplianceQuestion,
                                       ComplianceReport, ExecutableCheck,
                                       Finding, Requirement)
from agentos.domain.sources import Source, SourceKind
from agentos.identity.principal import Principal
from agentos.identity.roles import Role
from agentos.infra.model_router import ModelRouter
from agentos.infra.observability import Observability
from agentos.infra.tool_gateway import ToolGateway
from agentos.ingestion.chunker import Chunker
from agentos.ingestion.extraction import PlainTextExtractor
from agentos.ingestion.ingestor import DocumentIngestor
from agentos.knowledge.evidence_graph import EvidenceGraph
from agentos.knowledge.retrieval import GraphRAGRetriever
from agentos.security.classification import SensitivityClassifier
from agentos.security.encryption import EncryptionService
from agentos.security.policy import PolicyGuard
from agentos.security.store import SecureEvidenceStore


class ComplianceEngine:
    def __init__(self, ingestor: DocumentIngestor, planner: Planner,
                 retriever: RetrieverAgent, verifier: VerifierAgent,
                 sandbox: SandboxExecutorAgent, judge: JudgeAgent,
                 evidence_graph: EvidenceGraph, store: SecureEvidenceStore,
                 policy: PolicyGuard, observability: Observability) -> None:
        self.ingestor = ingestor
        self.planner = planner
        self.retriever = retriever
        self.verifier = verifier
        self.sandbox = sandbox
        self.judge = judge
        self.evidence_graph = evidence_graph
        self.store = store
        self.policy = policy
        self.observability = observability

    def run(self, question: ComplianceQuestion, principal: Principal) -> ComplianceReport:
        with self.observability.span("compliance.run", question_id=question.id,
                                     principal=principal.id) as run_span:
            for source in question.sources:
                with self.observability.span("ingest.document", source_id=source.id):
                    self.ingestor.ingest(source)

            findings: list[Finding] = []
            for claim in self.planner.decompose(question):
                with self.observability.span("assess.claim", claim_id=claim.id,
                                             executable=claim.is_executable) as claim_span:
                    findings.append(self._assess(claim, principal, claim_span))

            run_span.set("findings", len(findings))
            return ComplianceReport(question.id, findings, generated_at=datetime.now())

    def _assess(self, claim, principal, claim_span) -> Finding:
        candidate_span_ids = self.retriever.gather_evidence(claim, token_budget=2000)
        permitted_evidence = self.store.get_permitted(candidate_span_ids, principal)

        if claim.is_executable:
            support = self.sandbox.execute_for_ground_truth(claim, permitted_evidence)
            groundedness_score = support.groundedness_score
        else:
            support = self.verifier.verify(claim, permitted_evidence)
            groundedness_score = self.judge.score_groundedness(claim, support, permitted_evidence)

        evidence_tokens = sum(len(span.text.split()) for span in permitted_evidence)
        escalated = self.policy.requires_human_review(groundedness_score)

        claim_span.set("retrieved", len(candidate_span_ids))
        claim_span.set("permitted", len(permitted_evidence))
        claim_span.set("evidence.tokens", evidence_tokens)
        claim_span.set("verdict", support.verdict.value)
        claim_span.set("groundedness", groundedness_score)
        claim_span.set("escalated", escalated)

        self.evidence_graph.record_support(support)
        return Finding(
            requirement_id=claim.requirement_id,
            claim_id=claim.id,
            verdict=support.verdict,
            groundedness_score=groundedness_score,
            supporting_span_ids=support.evidence_span_ids,
            escalated_to_human=escalated,
        )


def build_engine() -> ComplianceEngine:
    models = ModelRouter()
    tools = ToolGateway()
    encryption = EncryptionService()
    policy = PolicyGuard()
    store = SecureEvidenceStore(encryption, policy)
    classifier = SensitivityClassifier()
    evidence_graph = EvidenceGraph()
    retriever = GraphRAGRetriever(evidence_graph)
    return ComplianceEngine(
        ingestor=DocumentIngestor(classifier, Chunker(), PlainTextExtractor(),
                                  store, evidence_graph, tools),
        planner=Planner("planner", models, tools),
        retriever=RetrieverAgent("retriever", models, tools, retriever),
        verifier=VerifierAgent("verifier", models, tools),
        sandbox=SandboxExecutorAgent("sandbox", models, tools),
        judge=JudgeAgent("judge", models, tools),
        evidence_graph=evidence_graph,
        store=store,
        policy=policy,
        observability=Observability(),
    )


if __name__ == "__main__":
    question = ComplianceQuestion(
        id="q1",
        text="Does the policy document satisfy data-retention rules?",
        requirements=[
            Requirement("r1", "Personal data is retained no longer than 24 months.",
                        ExecutableCheck("retention period", "months", CheckOperator.AT_MOST, 24)),
            Requirement("r2", "Data deletion requests are honored within 30 days."),
        ],
        sources=[Source("s1", SourceKind.PLAIN_TEXT, "samples/data_retention_policy.md")],
    )
    principal = Principal("u.owner", {Role.OWNER})
    engine = build_engine()
    report = engine.run(question, principal)
    print(f"Report {report.question_id} - {len(report.findings)} findings:")
    for finding in report.findings:
        print(f"  {finding.requirement_id}: {finding.verdict.value} "
              f"(score={finding.groundedness_score}, spans={len(finding.supporting_span_ids)}, "
              f"escalated={finding.escalated_to_human})")
    telemetry = engine.observability
    print(f"telemetry: spans={len(telemetry.spans)} "
          f"run_ms={telemetry.duration_of('compliance.run')} "
          f"evidence_tokens={int(telemetry.sum_attribute('evidence.tokens'))}")
