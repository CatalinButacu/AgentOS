# Agentic patterns in AgentOS

AgentOS is a **multi-agent workflow**: a structured, auditable control flow with specialized agents and genuine agentic patterns embedded. The control flow is a graph, not an open-ended autonomous loop — deliberate for compliance, where every decision path must be traceable.

This document maps the recognized agentic patterns to where they live in the code.

## The orchestration flow

```
START -> ingest -> plan --Send(per claim)--> assess --> review -> END
                                               |
                                     ┌─────────┴──────────┐
                             executable?                prose?
                                  |                        |
                            Sandbox(execute)      Verifier(Reflexion) -> Judge
                                  └──────────┬─────────────┘
                                          escalate? -> interrupt -> human -> resume
```

Defined in `agentos/engine.py` as a LangGraph `StateGraph`.

## Pattern inventory

| Pattern | In AgentOS | Code |
|---------|------------|------|
| Prompt chaining / sequential workflow | `ingest -> plan -> assess -> review -> report` | `ComplianceEngine._build_graph` |
| Orchestrator–workers | planner decomposes the question into claims; each claim is a worker task | `Planner.decompose`, `_assess` |
| Parallelization (sectioning) | one parallel `assess` branch per claim, results reduced | `_fan_out_claims` (`Send`) + `Annotated[..., operator.add]` |
| Routing | executable claim -> Sandbox; prose claim -> Verifier -> Judge | branch in `_assess` |
| Evaluator–optimizer | verifier proposes a verdict; independent judge scores groundedness and can overrule | `VerifierAgent`, `JudgeAgent` |
| Reflexion (self-reflection retry) | weak verification retries with a relaxed strategy | `VerifierAgent.reflect_and_retry` |
| ReAct (reason–act–observe) | retriever acts on the graph, observes evidence, reasoning consumes it | `RetrieverAgent.gather_evidence` -> `_assess` |
| RAG / GraphRAG | evidence retrieval grounds every verdict with provenance | `GraphRAGRetriever` |
| Tool use / verification-by-execution | numeric claims are executed for ground truth | `SandboxExecutorAgent` |
| Human-in-the-loop | escalation pauses the graph for a human decision, then resumes | `interrupt()` in `_review_node`, `Command(resume=...)` in `run` |
| Guardrails / policy | RBAC/ABAC access gating + groundedness threshold as control-flow guards | `PolicyGuard`, `AccessPolicy` |

## Pattern details

### Orchestrator–workers
`Planner.decompose` turns one `ComplianceQuestion` into a list of `Claim`s — the plan (a DAG of subtasks). The orchestrator then dispatches a worker per claim. This is plan-then-execute.

### Parallelization (sectioning)
`_fan_out_claims` emits one LangGraph `Send("assess", ...)` per claim, so claims are assessed in independent branches. Their `Finding`s are merged through the `operator.add` reducer on the `findings` channel.

### Routing
Inside `_assess`, `claim.is_executable` routes the claim: executable numeric rules go to the Sandbox (deterministic execution), prose claims go to the Verifier and then the Judge.

### Evaluator–optimizer (with separation of duties)
The `VerifierAgent` produces a verdict and cites supporting spans. The `JudgeAgent` **independently** re-scores groundedness over only the cited spans, applying a contradiction penalty the verifier's term-coverage cannot see. The judge's score — not the verifier's self-report — drives escalation, so the evaluator can overrule the optimizer.

### Reflexion
When strict verification falls below threshold, `VerifierAgent.reflect_and_retry` re-assesses with a relaxed matching strategy — a verbal self-reflection retry.

### RAG / GraphRAG
`GraphRAGRetriever` combines lexical (TF-IDF) seeds with semantic recall (embeddings), then traverses the evidence graph to attach each seed's parent section, under a token budget. Retrieval is what makes every verdict grounded and citable.

### Verification-by-execution
For claims that reduce to a checkable predicate (for example, "retention at most 24 months"), `SandboxExecutorAgent` parses the actual measured value from evidence and evaluates the rule deterministically — ground truth by execution rather than belief.

### Human-in-the-loop
`_review_node` calls `interrupt()` at the fan-in join when findings escalate. `run` resumes with `Command(resume=decision)` supplied by the configured `human_decider`, which overrides the verdict and clears escalation. Requires the checkpointer, compiled in only when a decider is configured.

## Two qualifiers

- **Workflow, not autonomous agent.** The control flow is a predefined graph, not an LLM choosing its own next actions in an open loop. The autonomous-agent pattern is the one canonical pattern deliberately avoided — auditable control flow is a compliance requirement.
- **Deterministic unless Azure OpenAI is wired.** Reasoning runs offline-deterministic by default; `ModelRouter` becomes real Azure OpenAI (completions + embeddings) when configured, upgrading the Verifier, Judge, and Retriever behind the same interfaces.

## References

- Anthropic, *Building Effective Agents* — prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer.
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*.
- Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning*.
- Microsoft Research, *GraphRAG*.
