# TraceIQ — Design Spec
**Date:** 2026-05-16 (updated 2026-05-17)
**Status:** Phase 2 shipped. Tier 2 large trace analysis in design.

---

## Problem

LLM systems (agents, RAG pipelines) fail silently. Existing trace stores (Langfuse, Arize Phoenix, LangSmith) collect spans but provide no AI-powered analysis layer. Developers have to read raw JSON to find root causes.

**TraceIQ is a framework-agnostic, Claude-powered trace analyzer** that connects to existing trace stores, builds an interaction graph per trace, and uses AI to surface root causes, annotate issues, and enable conversational debugging.

---

## The Scaling Problem (Discovered in Production)

Empirical measurement of a real production trace (faculty scraper, `325b79f92c9b00c6096b5aafba3d0443`):

| Metric | Value |
|---|---|
| Spans | 172 |
| Raw JSON size | 9.8 MB |
| Total content (inputs + outputs) | 7.58 MB |
| Avg content per span | 44 KB |
| Estimated tokens | ~1.94M |
| Claude context limit | ~200K tokens |
| Overflow factor | **9.7×** |

**Root cause of the overflow:** The trace is a 21-iteration agent loop where each `Prompt` span contains the full accumulated conversation history. By iteration 21, one span holds 265 KB. This is not pathological — it is the standard behavior of any stateful LLM agent.

**Failure mode of Tier 1 on large traces:**
- Context overflow → Claude call fails or truncates silently
- Even "lazy loading only flagged spans" fails: 30 flagged spans × 44 KB = 1.3 MB, still over limit

---

## Two-Tier Architecture

**Tier 1 (small traces, <50 spans):** Current pipeline. Works correctly. Untouched.

**Tier 2 (large traces, ≥50 spans):** New pipeline described below. Same AnalysisResult schema returned. Tiering is invisible to the user — same click, same UI.

The threshold (50 spans) is a starting point. Will be tuned based on observed content sizes.

---

## Tier 1: Small Trace Pipeline (shipped)

```
Adapter → GraphBuilder → AnomalyDetector → AnalysisEngine (single Claude call) → Cache
```

1. Fetch all spans from Phoenix (metadata only)
2. Build NetworkX directed graph (structural + causal edges)
3. Rule-based anomaly detection: 6 rules, no LLM
4. Load full content for flagged spans only (lazy)
5. Single Claude call: graph + flagged content → AnalysisResult
6. Cache in SQLite

Works for traces where total content of flagged spans fits comfortably in Claude's context window.

---

## Tier 2: Large Trace Pipeline (in development)

### Key Constraint: No Lossy Compression

RAPTOR-style LLM summarization was considered and rejected. For narrative text, paraphrasing is acceptable. For trace analysis, exact values matter:
- The precise error message in a span
- The exact selector that failed: `querySelector('.faculty-name')` returning `null`
- The specific iteration where token count spiked from 52K to 265K
- Exact tool call parameters

Summarizing any of this destroys the root cause. All compression must be **structural and lossless**.

---

### Stage 1: Trace Classification (free, <1ms)

`TraceClassifier` decides tier based on span count. If large, continues to Stage 2.

---

### Stage 2: Leiden Community Detection (no LLM, <50ms)

Run the Leiden algorithm on the span DAG. Leiden is the same algorithm used by Microsoft GraphRAG — proven at billion-edge scale, 403M edges/second.

For the faculty scraper trace, Leiden naturally identifies:
- `AgentLoop` — 21 iterations of [agent → should_continue → call_model → Prompt → ChatAnthropic]
- `ToolUse` — 20 tool spans + 11 browser_run_code_unsafe spans
- `OutputGeneration` — 2 generate_structured_response spans
- `Root` — FacultyScraper root span

No LLM involved. Pure graph partitioning on the parent-child edge structure.

**Why Leiden over simpler grouping:** Leiden correctly handles cases where the "natural" grouping is not just by span name — it finds structurally cohesive subgraphs even in traces with irregular patterns.

---

### Stage 3: Community Metadata Cards (lossless, computed not summarized)

For each community, compute a metadata card from raw span data. No LLM. No paraphrasing.

```json
{
  "community_id": "C1",
  "label": "AgentLoop",
  "span_count": 105,
  "span_types": ["agent", "should_continue", "call_model", "Prompt", "ChatAnthropic"],
  "iteration_count": 21,
  "avg_latency_ms": 4800,
  "total_latency_ms": 100800,
  "error_count": 0,
  "token_growth": {"first": 52000, "last": 265000, "delta": 213000},
  "anomalies": ["token_spike_at_iteration_4", "latency_spike_at_iteration_18"],
  "flagged_span_ids": ["s043", "s089"]
}
```

Everything is a computed statistic. Nothing is summarized. Claude reads these cards as structured data, not prose.

---

### Stage 4: Loop Deduplication (lossless, structural)

For the agent loop community, instead of 21 identical iterations:
- Keep iteration 1 (baseline state)
- Keep any iteration where something changed: anomaly detected, error, latency spike, output differed
- Keep iteration N (final state)
- Skip identical middle iterations

The "diff" between iterations is expressed as structured deltas (token count delta, latency delta, output hash changed: true/false) — not prose summaries. Exact values are preserved for kept iterations.

---

### Stage 5: Agentic Analysis via Claude Tool Use

Claude receives:
- All community metadata cards (~2,000 tokens total — down from 1.94M)
- The compressed loop structure (iteration 1 + anomalous iterations + iteration 21)
- A structured RCA SOP (based on Flow-of-Action architecture, 64% RCA accuracy proven at WWW 2025)

Claude has tools to retrieve exact data on demand:

```python
search_spans(query: str)           # semantic search over span metadata
get_community(community_id: str)   # full member list + metadata
drill_span(span_id: str)           # EXACT raw content of one span, no summarization
trace_causal_path(span_id: str)    # walk parent edges to root, return exact path
diff_iterations(community_id, i, j) # exact structural diff between two loop iterations
get_flagged_spans(community_id)    # spans flagged by Anomaly Detector in this community
```

Claude navigates the trace by calling tools. It only loads exact content for the 2-3 spans it actually needs. Nothing is summarized before reaching Claude. Everything Claude reads is the original raw data.

**RCA SOP (guides Claude's tool use sequence):**
1. Check for error-flagged communities first
2. In each flagged community: `get_flagged_spans` → `drill_span` on each
3. Trace causal path upward from errors
4. For loop communities with anomalies: `diff_iterations` on the anomalous iteration
5. Check if anomalies in one community correlate with issues in adjacent communities
6. Synthesize into AnalysisResult

---

### Stage 6: Same Output Schema

Tier 2 returns the same `AnalysisResult` as Tier 1. No changes to the frontend, cache, or API.

---

### Tier 2 Data Flow for Faculty Scraper Trace

```
172 spans, 1.94M tokens
        ↓
Stage 1: TraceClassifier → "large" (172 > 50) [<1ms]
        ↓
Stage 2: Leiden → 4 communities [<50ms, no LLM]
        ↓
Stage 3: Community metadata cards [<10ms, computed stats]
         Total: ~2,000 tokens
        ↓
Stage 4: Loop deduplication: 21 iterations → 3 kept [<5ms]
        ↓
Stage 5: Claude sees 2,000 tokens + calls tools
         Typical: 6-8 tool calls, each returning <10KB of exact raw data
         Total tokens sent to Claude: ~10,000 (vs. 1.94M → impossible)
        ↓
Stage 6: AnalysisResult (same schema)
Total latency: ~8-12s | Total cost: ~$0.05
```

---

## Competitive Landscape

| Tool | Closest feature | Gap |
|---|---|---|
| LangSmith "Polly" | AI trace Q&A | LangChain-only, proprietary, no large-trace handling |
| Galileo Signals | Automated failure detection | Enterprise paid, black box |
| Langfuse | Great trace store | No AI analysis layer |
| Arize Phoenix | OTel-based tracing | Evaluation-focused, not conversational |

**TraceIQ's position:** Open-source, framework-agnostic, handles both small and large traces correctly.

---

## Feasibility Basis

| Source | Finding | Application |
|---|---|---|
| LLMRCA (ACM 2025) | Causal graph from traces → 92.86% top-1 RCA accuracy | Tier 1 graph approach |
| SentinelAgent (arXiv 2026) | Directed interaction graph for multi-agent anomaly detection | Tier 1 graph structure |
| Flow-of-Action (WWW 2025) | SOP-guided multi-agent RCA → 64% accuracy vs 35% for naive ReAct | Tier 2 RCA SOP |
| GraphRAG / Leiden (Microsoft) | Leiden community detection proven at billion-edge scale | Tier 2 community detection |
| LazyGraphRAG (Microsoft 2025) | On-demand graph extraction → 700× cheaper than full GraphRAG | Tier 2 lazy tool retrieval |
| HippoRAG (NeurIPS 2024) | Personalized PageRank for multi-hop traversal → 10-20× cheaper than iterative | Tier 2 causal path traversal |
| OpenRCA (ICLR 2025) | RCA agent on 68GB telemetry via Python tool use | Tier 2 agentic architecture |
| Empirical (production trace) | 172-span trace = 9.8MB, 1.94M tokens = 9.7× Claude context limit | Confirms Tier 2 necessity |

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Runtime | Python 3.12, uv | |
| Backend | FastAPI | |
| Frontend | React + Vite + TypeScript | |
| LLM | Claude claude-sonnet-4-6 | Prompt caching enabled |
| Trace source | Arize Phoenix | Adapter pattern, easily swappable |
| Storage | SQLite | Analyses, chat history, settings |
| Graph (Tier 1) | networkx | In-memory, already installed |
| Community detection (Tier 2) | leidenalg | New dependency |
| Tool use (Tier 2) | Claude native tool use | No LangChain |

---

## Key Design Decisions

1. **Adapter pattern.** All trace sources implement the same abstract interface. Nothing above the adapter touches Phoenix types.

2. **Metadata-first graph.** Nodes carry metadata only. Content loaded lazily for flagged spans only.

3. **Rule-based pre-filter.** AnomalyDetector runs without LLM. Claude only sees pre-flagged spans.

4. **Prompt caching.** System prompt cached across chat turns on the same trace.

5. **No lossy compression.** RAPTOR-style LLM summarization explicitly rejected for trace content. Root causes live in exact values (error messages, parameters, token counts). All Tier 2 compression is structural (community grouping, loop deduplication) and fully lossless.

6. **Lossless loop deduplication.** For agent loops: keep first + changed + last iterations. Express changes as structured deltas, not prose. Exact content preserved for kept iterations.

7. **Agentic retrieval over bulk loading.** Tier 2 never pre-loads all span content. Claude requests exact spans on demand via tools. Nothing is summarized before Claude sees it.

8. **Same output schema across tiers.** Tier 2 returns identical AnalysisResult. Frontend, cache, and API unchanged.

9. **SQLite first.** No external infra. PostgreSQL migration path deferred to Phase 3.

---

## Phase 3 (Future)

- Cross-trace pattern detection (span embeddings + vector search across stored analyses)
- Continuous polling: background worker pulls new traces on interval
- Multi-adapter: LangSmith, Langfuse, Weave
- Alerting: Slack/email on critical issues
- PostgreSQL for multi-user scale
- Neo4j for cross-trace graph queries at scale
