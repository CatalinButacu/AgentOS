# AgentOS

An agentic **compliance-ingestion** system: ingest documents, verify requirements against evidence with a team of specialized agents, and produce audit-grade findings.

Guiding principle: **traceable, not infallible.** No LLM guarantees truth, so every finding carries its provenance (the exact cited spans) and an independent groundedness score; anything below threshold **escalates to a human**.

Built as a learning project for the Microsoft *Agentic AI Business Solutions Architect* certification. It runs fully offline and deterministic, and upgrades to Azure + Langfuse by setting environment variables — no code changes.

## Two theses

**1. Everything is one fractal graph, seen at many zoom levels.** The four graphs of agentic cognition are the coarsest view of a single structure:

| Graph | In this system |
|-------|----------------|
| **Knowledge** | `EvidenceGraph` — Document -> Section -> Chunk -> Span, with an inverted index and embeddings |
| **Orchestration** | a LangGraph `StateGraph` (`engine.py`) |
| **Plan** | the claim DAG the planner emits, fanned out per claim |
| **Memory** | bitemporal metadata on every span (`observed_at`, `effective_from/to`) |

**2. Retrieve at the coarsest level that answers the question.** Feeding a graph-retrieved neighborhood to reasoning uses far fewer tokens than stuffing the whole document — at equal answer quality. This is measured:

```
baseline (fat-context) evidence tokens: 418
frugal   (GraphRAG)    evidence tokens: 189
token reduction:                        54.8%
quality parity (verdicts):              True
```

Reproduce with `python -m agentos.benchmark`.

## The pipeline

```
identity/RBAC -> extract -> chunk -> dedup(Bloom) -> encrypt -> index+embed
   -> GraphRAG retrieve -> access-gate
   -> verify (Reflexion) | sandbox (execute)   -> judge (independent) -> escalate
   -> report -> telemetry
```

- **Extraction** — `PlainTextExtractor` offline; `AzureDocumentIntelligenceExtractor` for real PDFs/Office (layout model -> paragraphs with page/bbox).
- **Chunking** — layout-aware, deterministic, versioned; each span carries full provenance metadata.
- **Dedup** — content-addressed via a Bloom filter; identical content is stored/encrypted once, every span keeps its own provenance.
- **Security** — spans are encrypted at rest; RBAC (role -> sensitivity clearance) plus ABAC (tenant) gate every read.
- **Retrieval** — GraphRAG: TF-IDF lexical seeds + semantic recall (embeddings), then graph traversal to attach each seed's parent section, under a token budget.
- **Reasoning** — a `VerifierAgent` (term coverage + Reflexion retry) for prose claims; a `SandboxExecutorAgent` (parse the value, evaluate the rule) for numeric claims; an independent `JudgeAgent` (entailment minus a contradiction penalty) that can overrule the verifier. Verifier and judge are separated by design (separation of duties).
- **Observability** — OpenTelemetry-shaped spans with a `evidence.tokens` metric; optional `LangfuseExporter`.

See [`docs/agentic-patterns.md`](docs/agentic-patterns.md) for how the recognized agentic patterns map to this code.

## Layout

```
agentos/
  domain/      sources, compliance, graph          (the data model)
  identity/    roles, principal, access            (RBAC + ABAC)
  security/    encryption, classification, policy, store
  ingestion/   extraction, chunker, dedup, ingestor
  knowledge/   lexical, evidence_graph, retrieval
  agents/      base, planner, retriever, verifier, sandbox, judge
  infra/       model_router, tool_gateway, observability, langfuse_exporter
  engine.py    LangGraph orchestration
  benchmark.py frugality benchmark
samples/       example policy documents
```

## Run

Uses [uv](https://docs.astral.sh/uv/) for the environment.

```
uv venv
uv pip install -r requirements.txt
.venv\Scripts\python.exe -m agentos.engine
.venv\Scripts\python.exe -m agentos.benchmark
```

(On POSIX use `.venv/bin/python`.)

Only `engine.py` and `benchmark.py` need LangGraph; the individual modules are standard-library only.

## API

Run the HTTP service:

```
uv pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn agentos.api:app --reload
```

Check a document (auth via `X-API-Key`, default `dev-key`, override with `AGENTOS_API_KEY`):

```
curl -X POST http://localhost:8000/compliance/check ^
  -H "X-API-Key: dev-key" -H "Content-Type: application/json" ^
  -d "{\"question_id\":\"q\",\"requirements\":[{\"id\":\"r1\",\"text\":\"Personal data is retained no longer than 24 months.\"}],\"sources\":[{\"id\":\"s1\",\"kind\":\"plain_text\",\"uri\":\"samples/data_retention_policy.md\"}],\"principal\":{\"id\":\"o\",\"roles\":[\"owner\"]}}"
```

Set `AGENTOS_DB_PATH` to a file path to persist evidence across requests.

## Deploy

```
docker build -t agentos .
docker run -p 8000:8000 -e AGENTOS_API_KEY=change-me agentos
```

Tests run in CI on every push via `.github/workflows/ci.yml`.

## Going live on Azure

Every external integration is behind an interface with an offline fallback. Set the environment variables and install the optional dependencies to activate them — no code changes.

```
uv pip install -r requirements-azure.txt          # Document Intelligence + Azure OpenAI
uv pip install -r requirements-observability.txt  # Langfuse
```

| Capability | Class | Environment |
|------------|-------|-------------|
| Document extraction | `AzureDocumentIntelligenceExtractor` | `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY` |
| LLM + embeddings | `ModelRouter` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` |
| Trace export | `LangfuseExporter` | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |

## Method and conventions

- **Walking skeleton first, then replace component by component** — the whole loop was proven end-to-end offline before any cloud dependency was added.
- **Offline-deterministic core** — no external service is required to run or to reproduce the benchmark.
- **No comments in code** — explanation lives in documentation; identifiers carry intent.
- The Azure and Langfuse adapters are written to their SDKs but exercised only via the offline paths in this repository.
