# TraceIQ

Framework-agnostic, Claude-powered trace analyzer for LLM systems (agents, RAG pipelines). Connects to existing trace stores, builds an interaction graph per trace, uses AI to surface root causes and enable conversational debugging.

## Project Context

**Why this exists:** Existing tools (Langfuse, Arize Phoenix, LangSmith) collect spans but provide no AI analysis layer. Developers read raw JSON to find root causes. TraceIQ is the open-source, framework-agnostic Claude-powered analysis layer.

**Phase 2 (shipped):** Two-tier analysis engine — Tier 1 for small traces (<50 spans), Tier 2 for large traces (≥50 spans). Same dashboard, same click, same output schema. Phoenix as the first trace source.

**Phase 3 (future):** Cross-trace pattern detection, multi-adapter (LangSmith, Langfuse, Weave), continuous polling, alerting, PostgreSQL.

## Full Design Spec
`docs/superpowers/specs/2026-05-16-traceiq-design.md`

---

## Architecture: Two-Tier Analysis

### The Scaling Problem

Real production trace (faculty scraper, `325b79f92c9b00c6096b5aafba3d0443`):
- 172 spans | 9.8 MB raw JSON | 1.94M tokens of content
- Claude context limit: ~200K tokens → 9.7× over limit
- Root cause: 21-iteration agent loop where each Prompt span accumulates full conversation history (grows 52KB → 265KB)
- Tier 1 fails on this trace. Tier 2 handles it in ~10s.

---

### Tier 1: Small Trace Pipeline (<50 spans)

```
Adapter → GraphBuilder → AnomalyDetector → AnalysisEngine (single Claude call) → Cache
```

1. Fetch spans from Phoenix (metadata only)
2. Build NetworkX directed graph (structural + causal edges)
3. Rule-based anomaly detection (6 rules, no LLM)
4. Load exact content for flagged spans only (lazy)
5. Single Claude call: graph + flagged content → AnalysisResult
6. Cache in SQLite

---

### Tier 2: Large Trace Pipeline (≥50 spans)

No lossy compression. Root causes live in exact values — error messages, parameters, token counts. All compression is structural and lossless.

```
Stage 1: TraceClassifier → "large" (<1ms, no LLM)
Stage 2: Leiden community detection → 4-8 communities (<50ms, no LLM)
Stage 3: Community metadata cards (computed stats, no LLM, no paraphrasing)
Stage 4: Loop deduplication → keep first + changed + last iterations (lossless)
Stage 5: Agentic Claude analysis with tools
         Claude sees: ~2,000 tokens of structured metadata
         Claude calls: drill_span(), search_spans(), diff_iterations(), trace_causal_path()
         Each tool returns: EXACT raw data, never summarized
Stage 6: AnalysisResult (same schema as Tier 1)
```

**Why lossless matters:** RAPTOR-style LLM summarization was evaluated and rejected. Summarizing `querySelector('.faculty-name') → null` into "browser tool failed to find element" destroys the root cause.

**Community metadata card example:**
```json
{
  "label": "AgentLoop",
  "span_count": 105,
  "iteration_count": 21,
  "avg_latency_ms": 4800,
  "token_growth": {"first": 52000, "last": 265000},
  "anomalies": ["token_spike_at_iteration_4", "latency_spike_at_iteration_18"]
}
```

**Tools Claude can call:**
- `drill_span(span_id)` — exact raw content, no summarization
- `search_spans(query)` — find spans by metadata keyword
- `get_community(id)` — full member list + metadata card
- `trace_causal_path(span_id)` — walk parent edges to root
- `diff_iterations(community_id, i, j)` — exact structural diff between loop iterations
- `get_flagged_spans(community_id)` — anomaly detector flags in this community

---

## Data Flow

### Tier 1 (small trace)
1. Click trace → `GET /api/traces/{id}/analysis`
2. Cache hit → return instantly
3. Cache miss → fetch spans → graph → anomaly flags → load flagged content → single Claude call → cache → return

### Tier 2 (large trace, same endpoint)
1. Click trace → `GET /api/traces/{id}/analysis`
2. Cache hit → return instantly
3. Cache miss → fetch spans → classify as large → Leiden communities → metadata cards → loop dedup → agentic Claude (6-8 tool calls) → cache → return

Same frontend, same API, same AnalysisResult schema.

---

## Key Design Decisions

- **Adapter pattern** — abstract base class, Phoenix is first impl. New adapter = new file only.
- **Metadata-first graph** — nodes carry metadata only. Content loaded lazily on demand.
- **Rule-based pre-filter** — AnomalyDetector runs without LLM. 6 rules, always fast.
- **No lossy compression** — RAPTOR/LLM summarization explicitly rejected for trace content. Only structural compression (community grouping, loop deduplication).
- **Lossless loop deduplication** — keep first + changed + last iterations. Deltas expressed as structured numbers, not prose.
- **Agentic retrieval** — Claude requests exact span content on demand via tools. Never bulk-loaded, never pre-summarized.
- **Same output schema** — Tier 2 returns identical AnalysisResult. Frontend and cache unchanged.
- **Prompt caching** — system prompt cached across chat turns on the same trace.
- **SQLite first** — no external infra.

---

## Anomaly Detection Rules (Tier 1 + seeding Tier 2 communities)
- `error_status`: span.status == ERROR → severity ERROR
- `latency_spike`: span.latency > 2× median for span type → WARNING
- `loop_detected`: same span name 3+ times → ERROR
- `token_spike`: LLM span tokens > 2× project median → WARNING
- `causal_chain`: parent errored AND child failed → link causally
- `missing_output`: tool span output is null → WARNING

---

## Issue Output Schema (both tiers)
```json
{
  "issues": [{
    "id": "issue-1",
    "category": "failure | latency | quality | logic",
    "severity": "error | warning | info",
    "span_id": "abc123",
    "span_name": "browser_run_code_unsafe",
    "explanation": "...",
    "suggestion": "..."
  }],
  "root_cause": "...",
  "summary": "..."
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12, uv |
| Backend | FastAPI |
| Frontend | React + Vite + TypeScript |
| LLM | Claude claude-sonnet-4-6, prompt caching |
| Trace source | Arize Phoenix (adapter pattern) |
| Storage | SQLite (analyses, chat, settings) |
| Graph (Tier 1) | networkx |
| Community detection (Tier 2) | leidenalg |
| Tool use (Tier 2) | Claude native tool use |

---

## Feasibility Backing

| Source | Finding |
|---|---|
| Flow-of-Action WWW 2025 | SOP-guided agentic RCA → 64% accuracy vs 35% naive ReAct |
| Leiden / Microsoft GraphRAG | Community detection proven at billion-edge scale |
| LazyGraphRAG Microsoft 2025 | On-demand retrieval → 700× cheaper than pre-indexed GraphRAG |
| OpenRCA ICLR 2025 | RCA agent via tool use on 68GB telemetry → works at scale |
| LLMRCA ACM 2025 | Causal graph from traces → 92.86% top-1 RCA accuracy |
| Empirical (production trace) | 172 spans, 1.94M tokens confirms Tier 2 necessity |

---

## Project Files

- `src/traceiq/` — Python backend
- `frontend/` — React dashboard
- `generate_traces.py` — synthetic trace generator for testing
- `analyze_traces.py` — trace structure analysis tool
- `start_phoenix.py` — starts Phoenix locally (runs forever)
- `PROGRESS.md` — build progress and session resume guide
- `docs/superpowers/specs/` — design spec
- `docs/superpowers/plans/` — implementation plans

## Running Locally

```bash
# Start Phoenix
nohup uv run python start_phoenix.py > /tmp/phoenix.log 2>&1 &

# Send test traces (after each Phoenix restart — it's in-memory)
uv run python generate_traces.py

# Start TraceIQ dashboard
uv run traceiq
# → http://localhost:8000
```

Phoenix settings (URL + project) configurable via ⚙ gear icon in dashboard without editing .env.
