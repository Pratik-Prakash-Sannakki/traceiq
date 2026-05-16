# TraceIQ — Design Spec
**Date:** 2026-05-16
**Status:** Approved for Phase 2 implementation

---

## Problem

LLM systems (agents, RAG pipelines) fail silently. Existing trace stores (Langfuse, Arize Phoenix, LangSmith) collect spans but provide no AI-powered analysis layer. Developers have to read raw JSON to find root causes. At scale, patterns across thousands of traces are invisible.

**TraceIQ is a framework-agnostic, Claude-powered trace analyzer** that connects to existing trace stores, builds an interaction graph per trace, and uses AI to surface root causes, annotate issues, and enable conversational debugging.

---

## Feasibility Basis

- **LLMRCA (ACM 2025):** Heterogeneous causal graph from traces → 92.86% top-1 RCA accuracy, 5.1× better than baselines
- **SentinelAgent (arXiv May 2026):** Directed interaction graph for multi-agent systems → detects loops, errors, collusive delegation
- **LazyGraphRAG (Microsoft):** Deferred graph construction at query time → 0.1% cost of full GraphRAG at comparable quality
- **Empirical:** Synthetic Phoenix traces measured at 7–9 KB raw JSON, 12–18 spans. Graph structure is always small; content payload is what grows.

---

## Competitive Landscape

| Tool | Closest feature | Gap |
|---|---|---|
| LangSmith "Polly" | AI trace Q&A | LangChain-only, proprietary |
| Galileo Signals | Automated failure detection | Enterprise paid, black box |
| Langfuse | Great trace store | No AI analysis layer |
| Arize Phoenix | OTel-based tracing | Evaluation-focused, not conversational |

**TraceIQ's position:** Open-source, framework-agnostic, Claude-powered analysis. Plug into any trace store.

---

## Architecture

### The Two Problems
1. **Per-trace:** Debug a specific bad run — why did this fail?
2. **Cross-trace:** Spot patterns across thousands of runs — what keeps failing?

Phase 2 solves #1. Phase 3 adds #2.

### Layers

```
Dashboard (React + FastAPI)
        ↓ REST API
┌─────────────────────────────────┐
│  Trace Adapter                  │  Fetches + normalizes spans
│  Graph Builder                  │  In-memory directed graph (metadata only)
│  Anomaly Detector               │  Rule-based flagging (no LLM)
│  Analysis Engine (Claude)       │  Graph + flagged content → issue list
│  Cache (SQLite)                 │  Stores results + chat history
└─────────────────────────────────┘
        ↓
  Arize Phoenix (Phase 2 adapter)
  + LangSmith, Langfuse, Weave (Phase 3 adapters)
```

### Layer 1 — Trace Adapter
Abstract base class: `list_traces(limit, filters)`, `get_trace(id)`, `get_spans(trace_id)`.
First implementation: Arize Phoenix REST API.
Normalizes all span data into internal `Span` dataclass — nothing above this layer touches Phoenix types.

### Layer 2 — Graph Builder
Builds a directed interaction graph in memory from normalized spans.

**Nodes:** One per span. Carries metadata only (name, type, latency, token counts, status, error message). Full input/output text is NOT loaded here.

**Edge types:**
- `structural`: parent → child (from `parent_id`)
- `data-flow`: span A's output hash matches span B's input hash (retriever → LLM)
- `causal`: span A errored and span B failed within 100ms (derived relationship)

Build time: O(n) over spans. No LLM. For 18-span trace: <5ms.

### Layer 3 — Anomaly Detector
Pure rule-based graph walk. Flags suspicious node IDs without any LLM call.

Rules:
- `error_status`: span status = ERROR → severity ERROR
- `latency_spike`: span latency > 2× median for that span type → severity WARNING
- `loop_detected`: same span name appears 3+ times in sequence → severity ERROR
- `token_spike`: LLM span tokens > 2× median for project → severity WARNING
- `causal_chain`: parent errored AND child also failed → link them explicitly
- `missing_output`: tool span has null output → severity WARNING

Output: list of `(span_id, rule, severity)` tuples. Typically 2-5 flags per trace.

### Layer 4 — Analysis Engine
Single Claude call per trace. Input:

1. Full graph structure (all nodes + edges with metadata) — always small
2. Full `input` + `output` content ONLY for flagged spans — controlled size
3. Structured prompt: reason step-by-step through the graph, identify root causes, return JSON

**Output schema:**
```json
{
  "issues": [
    {
      "id": "issue-1",
      "category": "failure | latency | quality | logic",
      "severity": "error | warning | info",
      "span_id": "abc123",
      "span_name": "web-search-attempt-1",
      "explanation": "Rate limit error on web search caused the agent to retry 3 times, adding 2.1s of latency before succeeding.",
      "suggestion": "Add exponential backoff or switch to a secondary search provider on rate limit."
    }
  ],
  "root_cause": "Rate limiting on web-search tool triggered a 3-iteration retry loop.",
  "summary": "Agent completed successfully but with unnecessary latency due to unhandled rate limits."
}
```

Model: `claude-sonnet-4-6`. Prompt caching enabled for the system prompt.

### Layer 5 — Cache
SQLite. Three tables:
- `traces`: snapshot of span metadata at analysis time
- `analyses`: Claude's output per trace, keyed by trace_id
- `chat_messages`: conversation history per trace

Cache invalidation: manual only (user clicks "Re-analyze").

Phase 3: swap SQLite → PostgreSQL. No other changes.

### Layer 6 — Dashboard
**Backend:** FastAPI. Endpoints:
- `GET /api/traces` — list traces with issue counts
- `GET /api/traces/{id}/analysis` — get or trigger analysis
- `POST /api/traces/{id}/chat` — send message, stream Claude response

**Frontend:** React. Two-panel layout:
- Left: trace list, sortable by severity/latency/time, filterable by status
- Right: trace tree with issues annotated inline per span + issue summary panel + chat

Single entrypoint: `uv run traceiq` starts FastAPI + serves React build.

---

## Data Flow (Per-Trace Analysis)

```
1. User clicks trace in list
2. GET /api/traces/{id}/analysis
3. Backend checks SQLite cache → hit: return instantly
4. Cache miss:
   a. Adapter fetches all spans from Phoenix
   b. Graph Builder constructs in-memory graph (metadata only)
   c. Anomaly Detector flags 2-5 suspicious spans
   d. Fetch full input/output content for flagged spans only
   e. Claude call: graph + flagged content → issue list JSON
   f. Save to SQLite cache
5. Return issue list to frontend
6. Frontend annotates each span in the trace tree with its issues
```

---

## Phase 3 Additions (not in scope now)

- **Persistent KG:** merge each trace graph into a global graph DB (Neo4j or SQLite with adjacency tables). Enables cross-trace queries: "all traces where reranker latency > 400ms."
- **Span embeddings:** embed each span for semantic search across trace corpus.
- **Continuous polling:** background worker pulls new traces from Phoenix every N minutes.
- **Alerting:** Slack/email digest of critical issues.
- **Multi-adapter:** LangSmith, Langfuse, Weave adapters.
- **PostgreSQL:** replace SQLite for multi-user scale.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12, uv |
| Backend | FastAPI |
| Frontend | React |
| LLM | Claude API (`claude-sonnet-4-6`), prompt caching |
| Trace source (Phase 2) | Arize Phoenix |
| Storage | SQLite |
| Graph (in-memory) | Python dicts + networkx |

---

## Key Design Decisions

1. **Adapter pattern from day 1.** All trace sources implement the same abstract interface. Business logic never touches Phoenix types.
2. **Metadata-first graph.** Build the graph with metadata only. Pull content lazily for flagged spans only. Keeps context window manageable even for large traces.
3. **Rule-based pre-filter before LLM.** Anomaly Detector runs without any LLM call. Claude only sees what the rules have already flagged as suspicious.
4. **Prompt caching.** System prompt + graph structure cached across chat messages on the same trace. Reduces cost significantly for multi-turn conversations.
5. **SQLite first.** No infra to set up. Explicit migration path to PostgreSQL for Phase 3.
6. **Shape the problem as we build.** Architecture intentionally kept lean for Phase 2. Cross-trace KG deferred to Phase 3 once we understand real-world trace patterns better.
