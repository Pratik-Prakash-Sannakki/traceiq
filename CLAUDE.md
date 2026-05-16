# TraceIQ

Framework-agnostic, Claude-powered trace analyzer for LLM systems (agents, RAG pipelines). Connects to existing trace stores, builds an interaction graph per trace, and uses AI to surface root causes, annotate issues, and enable conversational debugging.

## Project Context

**Why this exists:** Existing tools (Langfuse, Arize Phoenix, LangSmith) collect spans but provide no AI analysis layer. Developers read raw JSON to find root causes. TraceIQ is the open-source, framework-agnostic analysis layer that plugs into any trace store.

**Phase 2 (current):** Single-page dashboard connected to Arize Phoenix. Per-trace: build interaction graph → rule-based anomaly detection → Claude analysis → annotated view + chat.

**Phase 3 (future):** Persistent cross-trace KG, span embeddings, continuous polling, alerting, multi-adapter (LangSmith, Langfuse, Weave), PostgreSQL.

## Full Design Spec
`docs/superpowers/specs/2026-05-16-traceiq-design.md`

## Architecture (Phase 2)

```
Dashboard (React + FastAPI)
        ↓ REST API
Trace Adapter       → fetches + normalizes spans from Phoenix
Graph Builder       → in-memory directed graph (metadata only, no LLM)
Anomaly Detector    → rule-based flagging (error, latency, loop, token spike)
Analysis Engine     → Claude: graph + flagged span content → issue list JSON
Cache (SQLite)      → stores results + chat history
        ↓
Arize Phoenix REST API
```

## Data Flow (Per-Trace)

1. User clicks trace → `GET /api/traces/{id}/analysis`
2. Check SQLite cache → hit: return instantly
3. Cache miss: fetch spans → build graph → flag anomalies → fetch content for flagged spans only → Claude call → cache → return
4. Frontend annotates trace tree with issues inline
5. User chats with Claude about the trace (full graph + analysis as context)

## Key Design Decisions

- **Adapter pattern from day 1** — abstract base class, Phoenix is first impl. Adding LangSmith = new file only.
- **Metadata-first graph** — graph nodes carry metadata only. Pull full input/output lazily for flagged spans only. Keeps Claude context manageable.
- **Rule-based pre-filter** — Anomaly Detector runs without LLM. Claude only sees pre-flagged suspicious spans.
- **Prompt caching** — system prompt + graph structure cached across chat turns. Reduces cost on multi-turn conversations.
- **SQLite first** — no infra required. Explicit migration path to PostgreSQL for Phase 3.
- **Shape as we build** — cross-trace KG deferred to Phase 3 once real-world trace patterns are understood.

## Anomaly Detection Rules
- `error_status`: span.status == ERROR → severity ERROR
- `latency_spike`: span.latency > 2× median for span type → WARNING
- `loop_detected`: same span name 3+ times in sequence → ERROR
- `token_spike`: LLM span tokens > 2× project median → WARNING
- `causal_chain`: parent errored AND child failed within 100ms → link causally
- `missing_output`: tool span output is null → WARNING

## Issue Output Schema
```json
{
  "issues": [{
    "id": "issue-1",
    "category": "failure | latency | quality | logic",
    "severity": "error | warning | info",
    "span_id": "abc123",
    "span_name": "web-search-attempt-1",
    "explanation": "...",
    "suggestion": "..."
  }],
  "root_cause": "...",
  "summary": "..."
}
```

## Tech Stack
- Runtime: Python 3.12, uv
- Backend: FastAPI
- Frontend: React
- LLM: Claude API (`claude-sonnet-4-6`), prompt caching enabled
- Trace source: Arize Phoenix (Phase 2)
- Storage: SQLite → PostgreSQL (Phase 3)
- Graph: Python dicts + networkx (in-memory)

## Feasibility Backing
- LLMRCA (ACM 2025): causal graph from traces → 92.86% top-1 RCA accuracy
- SentinelAgent (arXiv 2026): directed interaction graph for multi-agent anomaly detection
- LazyGraphRAG (Microsoft): deferred graph construction → viable at query time
- Empirical: Phoenix synthetic traces measured at 7–9 KB, 12–18 spans. Graph structure always fits in context.

## Project Files
- `generate_traces.py` — generates synthetic traces for testing
- `analyze_traces.py` — pulls traces from Phoenix and prints structure analysis
- `start_phoenix.py` — starts Phoenix server locally
- Resume: `~/Downloads/Pratik_P_S_resume.pdf`
