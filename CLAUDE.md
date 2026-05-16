# TraceIQ

Framework-agnostic, Claude-powered trace analyzer for LLM systems (agents, RAG pipelines). Connects to existing trace stores, runs AI analysis, surfaces categorized issues, and lets you chat with Claude about any trace.

## Project Context

**Why this exists:** Existing tools (LangSmith, Langfuse, Arize) are great trace stores but lack a serious AI analysis layer. LangSmith's "Polly" is the closest thing but is LangChain-only and proprietary. TraceIQ is the open-source, framework-agnostic version.

**Phase 2 (current):** Single-page dashboard — trace list + AI analysis panel + inline chat. Langfuse as the first trace source.

**Phase 3 (future):** Persistent backend, continuous polling, proactive alerting (Slack/email), trend charts, PostgreSQL, multi-user.

## Architecture

```
Frontend (React)
    ↕ REST API
Backend (FastAPI)
    ├── Trace Adapter Layer   ← abstract interface, Langfuse is first impl
    ├── Analysis Engine       ← Claude API, returns structured issues
    └── Cache (SQLite)        ← stores results + chat history
    ↓                ↓
Langfuse API      Claude API
```

## Components

### Trace Adapter
Abstract base class with: `list_traces(limit, filters)`, `get_trace(id)`, `get_spans(trace_id)`.
Langfuse is `adapters/langfuse.py`. Adding LangSmith = new file, nothing else changes.

### Analysis Engine
Sends full trace (spans, inputs, outputs, latency, errors) to Claude.
Returns structured issues, each with:
- **category**: `failure | latency | quality | logic`
- **severity**: `error | warning | info`
- **span_id**: which span the issue is on
- **explanation**: what went wrong and why
- **suggestion**: how to fix it

### Cache Layer
SQLite. Stores: trace snapshots, analysis results, chat history per trace.
Phase 3: swap to PostgreSQL — zero changes in other layers.

### Web Dashboard
FastAPI + React. Two-panel layout:
- Left: trace list with filters (date, status, latency, tags)
- Right: annotated trace view + inline Claude chat

Single entrypoint: `uv run traceiq`

## Design Decisions

- **Adapter pattern from day 1** — all trace sources implement the same abstract interface. Never couple business logic to Langfuse-specific types.
- **SQLite first** — no infra to set up, easy to ship. Explicit migration path to PostgreSQL for Phase 3.
- **Claude as the analyst** — analysis prompt should ask Claude to reason step-by-step through the trace, not just pattern-match on error strings.
- **Cache analysis results** — Claude calls are expensive. Never re-analyze a trace unless the user explicitly requests it.

## Tech Stack

- **Runtime:** Python 3.12, uv
- **Backend:** FastAPI
- **Frontend:** React
- **LLM:** Claude API (claude-sonnet-4-6)
- **Trace source (Phase 2):** Langfuse
- **Storage:** SQLite (Phase 2) → PostgreSQL (Phase 3)

## Issue Categories

| Category | Examples |
|---|---|
| `failure` | Tool errors, exceptions, failed LLM calls, timeouts |
| `latency` | Slow spans, expensive runs, anomalous token usage |
| `quality` | Bad retrieval chunks, hallucinations, off-topic responses |
| `logic` | Agent loops, wrong tool selection, missed steps, repeated calls |
