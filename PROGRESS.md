# TraceIQ — Build Progress

## Plan File
`docs/superpowers/plans/2026-05-16-traceiq-phase2.md`

## Design Spec
`docs/superpowers/specs/2026-05-16-traceiq-design.md`

## GitHub
https://github.com/Pratik-Prakash-Sannakki/traceiq

---

## Status: Phase 2 COMPLETE ✅

All 8 tasks shipped + Phoenix settings UI added.

| # | Task | Status |
|---|---|---|
| 1 | Project setup + core models | ✅ |
| 2 | Trace Adapter (abstract base + Phoenix) | ✅ |
| 3 | Graph Builder (NetworkX) | ✅ |
| 4 | Anomaly Detector (6 rules) | ✅ |
| 5 | Analysis Engine (Claude API + prompt caching) | ✅ |
| 6 | SQLite Cache (analyses + chat history) | ✅ |
| 7 | FastAPI Backend + Pipeline | ✅ |
| 8 | React Frontend (trace list, issue panel, chat) | ✅ |
| + | Phoenix connection settings UI | ✅ |

**Tests:** 29 passing

---

## How to Run

```bash
cd ~/Documents/traceiq

# Start Phoenix (trace store)
nohup uv run python start_phoenix.py > /tmp/phoenix.log 2>&1 &

# Generate test traces (first time or after Phoenix restart)
uv run python generate_traces.py

# Start TraceIQ dashboard
uv run traceiq
```

- **TraceIQ:** http://localhost:8000
- **Phoenix:** http://localhost:6006
- **Settings:** click ⚙ in trace list header to configure Phoenix URL/project

---

## Architecture (implemented)

```
React Dashboard (http://localhost:8000)
    ↕ REST API (FastAPI)
Trace Adapter  →  PhoenixAdapter (GET /v1/projects/{project}/spans)
Graph Builder  →  NetworkX DiGraph (structural + causal edges, metadata-only nodes)
Anomaly Detector → 6 rules: error_status, latency_spike, loop_detected,
                             token_spike, missing_output, causal_chain
Analysis Engine → Claude claude-sonnet-4-6 (prompt caching, JSON output, streaming chat)
Cache          → SQLite (analyses, chat_messages, settings tables)
```

## Key Files
- `src/traceiq/models.py` — Span, TraceInfo, Flag, Issue, AnalysisResult
- `src/traceiq/adapters/phoenix.py` — Phoenix REST adapter
- `src/traceiq/graph/builder.py` — GraphBuilder
- `src/traceiq/graph/anomaly.py` — AnomalyDetector
- `src/traceiq/analysis/engine.py` — AnalysisEngine (Claude)
- `src/traceiq/analysis/prompts.py` — SYSTEM_PROMPT + build_user_message
- `src/traceiq/cache/db.py` — SQLiteCache
- `src/traceiq/api/pipeline.py` — run_analysis() orchestrator
- `src/traceiq/api/routes.py` — FastAPI routes
- `src/traceiq/cli.py` — `uv run traceiq` entrypoint
- `frontend/src/App.tsx` — root layout
- `frontend/src/components/` — TraceList, IssuePanel, Chat, Settings

## Phase 3 (future)
- Persistent KG across traces (Neo4j or SQLite adjacency tables)
- Span embeddings + clustering for cross-trace pattern detection
- Continuous polling + Slack/email alerts
- LangSmith, Langfuse, Weave adapters
- PostgreSQL for multi-user scale

## .env (local only, NOT in git)
```
ANTHROPIC_API_KEY=<your-key>
PHOENIX_URL=http://localhost:6006
PHOENIX_PROJECT=default
TRACEIQ_DB_PATH=traceiq.db
```

## Notes
- Phoenix loses traces on restart (in-memory) — re-run generate_traces.py after each restart
- API key rotation needed — previous key was exposed in git history, rotate at console.anthropic.com
