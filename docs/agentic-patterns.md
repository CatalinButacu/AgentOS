# Agentic patterns in AgentOS

AgentOS is a **multi-agent workflow**: a structured, auditable control flow with specialized agents and genuine agentic patterns embedded. The control flow is a graph, not an open-ended autonomous loop — deliberate for compliance, where every decision path must be traceable.

This document maps the recognized agentic patterns to where they live in the code, using the vocabulary from IBM's *AI agents* reference and the primary literature.

## Reasoning paradigm: ReWOO at the macro level, Reflexion inside

The literature names three reasoning paradigms for agents (IBM, *Agentic reasoning*):

- **ReAct** (Reason + Act) — an interleaved Thought → Action → Observation loop; the model re-plans after every tool result. Strong on open, uncertain tasks, but it can repeat itself into infinite loops and is harder to audit.
- **ReWOO** (Reasoning WithOut Observation) — a **planner → worker → solver** pipeline that plans the whole task upfront, executes without observation-in-the-loop, then synthesizes. More token-efficient and more robust to tool failure when the plan is knowable in advance.
- **Reflexion** — verbal self-feedback: after a weak attempt, the agent critiques its own result and retries.

**AgentOS is ReWOO-structured, by design.** `Planner.decompose` turns a `ComplianceQuestion` into the full set of claims *before* any evidence is seen (the planner); each claim is assessed independently (the workers); `_review_node` and the report assemble the findings (the solver). This is the right paradigm for compliance: the plan — which requirements to check — is knowable upfront, token cost is bounded, and a single tool failure degrades one claim instead of derailing an open reasoning loop. **Reflexion** lives *inside* a worker: `VerifierAgent.reflect_and_retry` re-assesses a below-threshold verdict with a relaxed matching strategy.

We deliberately avoid an open **ReAct** loop. IBM's own material flags ReAct's infinite-loop failure mode; for an auditable compliance engine, plan-then-execute (ReWOO) over a fixed graph is both safer and cheaper. If an open loop were ever introduced, it would require the standard guardrails — a hard max-iteration cap and the tool activity log described below.

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

## Retrieval is Corrective RAG

IBM's corrective-RAG pattern: retrieve → grade relevance → verify → generate under constraint → refuse when ungrounded. AgentOS follows this spine:

- `GraphRAGRetriever` retrieves the smallest grounded evidence set under a token budget (retrieve).
- `SecureEvidenceStore.get_permitted` gates that set by RBAC/ABAC before it reaches reasoning (an access/source filter).
- `JudgeAgent` independently scores groundedness over only the cited spans (grade).
- `PolicyGuard.requires_human_review` escalates anything below the groundedness threshold to a human instead of emitting an unsupported verdict (refuse / correct).

Every verdict cites the exact spans it stands on — provenance, not belief.

## Tool calling

`ToolGateway` is a real tool registry following IBM's tool-calling component: each tool carries a **name, description and required parameters**; `describe()` exposes them for selection; `call()` validates the tool and its arguments, runs the handler, captures errors as data rather than raising, and records every invocation in an **activity log**. The reasoning-with-tools step is genuinely tool-mediated — `RetrieverAgent` calls `retrieve_evidence` and `SandboxExecutorAgent` calls `measure_metric` through the gateway (`agents/retriever.py`, `agents/sandbox.py`), so every action is logged and uniform.

## Memory

Mapped to the CoALA memory taxonomy (IBM, *AI agent memory*):

- **Long-term / semantic** — the `EvidenceGraph`: nodes, an inverted index and embeddings, persisted through the `KeyValueStore` backend.
- **Episodic** — `support_links`: the record of what was decided for each claim, with its citations.
- **Short-term / working** — the per-run `ComplianceState` carried across graph nodes.

## Pattern inventory

| Pattern | In AgentOS | Code |
|---------|------------|------|
| Reasoning paradigm — ReWOO (plan → work → solve) | planner decomposes upfront; workers assess per claim; review/report synthesizes | `Planner.decompose`, `_assess`, `_review_node` |
| Reflexion (self-reflection retry) | weak verification retries with a relaxed strategy | `VerifierAgent.reflect_and_retry` |
| Corrective RAG | retrieve -> grade groundedness -> escalate/refuse below threshold | `GraphRAGRetriever`, `JudgeAgent`, `PolicyGuard` |
| Tool calling (registry + activity log) | named tools with parameters, logged invocations | `ToolGateway`, `retrieve_evidence`, `measure_metric` |
| Prompt chaining / sequential workflow | `ingest -> plan -> assess -> review -> report` | `ComplianceEngine._build_graph` |
| Orchestrator–workers | planner decomposes the question into claims; each claim is a worker task | `Planner.decompose`, `_assess` |
| Parallelization (sectioning) | one parallel `assess` branch per claim, results reduced | `_fan_out_claims` (`Send`) + `Annotated[..., operator.add]` |
| Routing | executable claim -> Sandbox; prose claim -> Verifier -> Judge | branch in `_assess` |
| Evaluator–optimizer | verifier proposes a verdict; independent judge scores groundedness and can overrule | `VerifierAgent`, `JudgeAgent` |
| RAG / GraphRAG | evidence retrieval grounds every verdict with provenance | `GraphRAGRetriever` |
| Verification-by-execution | numeric claims are executed for ground truth | `SandboxExecutorAgent` |
| Human-in-the-loop | escalation pauses the graph for a human decision, then resumes | `interrupt()` in `_review_node`, `Command(resume=...)` in `run` |
| Guardrails / policy | RBAC/ABAC access gating + groundedness threshold as control-flow guards | `PolicyGuard`, `AccessPolicy` |

## Pattern details

### ReWOO (planner–worker–solver)
`Planner.decompose` turns one `ComplianceQuestion` into a list of `Claim`s — the plan — with no dependence on evidence yet observed. The orchestrator dispatches a worker per claim (`_assess`), each of which retrieves and reasons independently. `_review_node` and `ComplianceReport` act as the solver, synthesizing the workers' findings into a single answer. Because the plan is fixed before execution, a failure in one worker's tool call degrades only that claim.

### Evaluator–optimizer (with separation of duties)
The `VerifierAgent` produces a verdict and cites supporting spans. The `JudgeAgent` **independently** re-scores groundedness over only the cited spans, applying a contradiction penalty the verifier's term-coverage cannot see. The judge's score — not the verifier's self-report — drives escalation, so the evaluator can overrule the optimizer.

### Reflexion
When strict verification falls below threshold, `VerifierAgent.reflect_and_retry` re-assesses with a relaxed matching strategy — a verbal self-reflection retry.

### Verification-by-execution
For claims that reduce to a checkable predicate (for example, "retention at most 24 months"), `SandboxExecutorAgent` measures the actual value from evidence and evaluates the rule deterministically — ground truth by execution rather than belief.

### Human-in-the-loop
`_review_node` calls `interrupt()` at the fan-in join when findings escalate. `run` resumes with `Command(resume=decision)` supplied by the configured `human_decider`, which overrides the verdict and clears escalation. Requires the checkpointer, compiled in only when a decider is configured.

## Best practices satisfied

IBM lists best practices for trustworthy agents; AgentOS already implements several:

- **Activity logs** — `Observability` spans across the run, plus the `ToolGateway` call log — for transparency and debugging.
- **Interruptibility / human approval before high-impact actions** — `interrupt()` pauses the graph for a human decision on low-groundedness findings before they become results.
- **Least privilege** — RBAC/ABAC access gating restricts every principal to the evidence it is cleared to read.
- **Bounded execution** — a fixed graph rather than an open loop, which is the named cure for infinite loops.

## Two qualifiers

- **Workflow, not autonomous agent.** The control flow is a predefined graph, not an LLM choosing its own next actions in an open loop. This is a deliberate compliance requirement, and — per the ReWOO analysis above — also the more efficient and failure-robust choice for a task whose plan is knowable upfront.
- **Deterministic unless Azure OpenAI is wired.** Reasoning runs offline-deterministic by default; `ModelRouter` becomes real Azure OpenAI (completions + embeddings) when configured, upgrading the Verifier, Judge and Retriever behind the same interfaces.

## References

- IBM Think — *What are AI agents?*, *Agentic reasoning*, *AI agent memory*, *Tool calling*, *What is ReWOO?*
- Anthropic, *Building Effective Agents* — prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer.
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*.
- Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning*.
- Xu et al., *ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models*.
- Microsoft Research, *GraphRAG*.
