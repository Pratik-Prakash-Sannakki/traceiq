# TraceIQ

AI-powered root cause analysis for LLM application traces. Connect to Phoenix or LangSmith, select a trace, and get a structured diagnosis — issues, root cause, and recommended fixes — powered by Claude.

---

## What it does

- **Connects** to Arize Phoenix or LangSmith and pulls your traces
- **Analyzes** traces using a two-tier Claude-powered engine:
  - Small traces → single Claude call with full span context
  - Large traces → community detection + agentic multi-turn investigation
- **Surfaces** root cause, categorized issues (Failure / Latency / Logic / Quality), and actionable fixes
- **Chat** — ask follow-up questions about any trace in natural language
- **Filters** traces by status (Failing / Degraded / Healthy) directly from the sidebar

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python 3.12 |
| Analysis | Anthropic Claude (Sonnet) |
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 |
| Storage | SQLite (analysis cache + settings) |
| Observability | Arize Phoenix, LangSmith |

---

## Getting started

### Prerequisites

- Python 3.12+
- Node 18+
- An [Anthropic API key](https://console.anthropic.com)
- A running [Arize Phoenix](https://github.com/Arize-ai/phoenix) instance **or** a [LangSmith](https://smith.langchain.com) account

### 1. Clone and install

```bash
git clone <repo>
cd traceiq

# Backend
uv sync

# Frontend
cd frontend && npm install && npm run build && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Phoenix (default)
PHOENIX_URL=http://localhost:6006
PHOENIX_PROJECT=default

# LangSmith (optional)
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=default
```

### 3. Run

```bash
uv run --env-file .env uvicorn traceiq.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

---

## Connecting a data source

Click the gear icon in the sidebar → select **Phoenix** or **LangSmith** → enter credentials → **Connect**.

The connection is tested immediately — you will see how many traces were found before the modal closes.

### Phoenix

| Field | Value |
|-------|-------|
| Phoenix URL | `http://localhost:6006` (or your hosted URL) |
| Project | Your Phoenix project name |

### LangSmith

| Field | Value |
|-------|-------|
| Host | `https://api.smith.langchain.com` |
| API Key | Generate at smith.langchain.com → Settings → API Keys |
| Project | Your LangSmith project name |

---

## How analysis works

**Tier 1 (fewer than 50 spans)** — Single Claude call with the full span graph, flagged anomalies, and span content.

**Tier 2 (50+ spans)** — Multi-stage pipeline:
1. Graph construction + anomaly detection (latency spikes, error cascades, token growth, loops)
2. Community detection groups spans into functional clusters
3. Community cards + loop compression summarises each cluster for the agent
4. Claude agent with tools (`drill_span`, `search_spans`, `trace_causal_path`, `diff_iterations`, `finish_analysis`) investigates iteratively and submits structured findings

Results are cached in SQLite. Re-analyze any trace from the header.

---

## Project structure

```
traceiq/
├── src/traceiq/
│   ├── adapters/        # Phoenix + LangSmith connectors
│   ├── analysis/        # Claude analysis engine + agent
│   ├── api/             # FastAPI routes, pipeline, settings
│   ├── cache/           # SQLite cache
│   ├── graph/           # Graph builder, anomaly detection, communities
│   └── models.py        # Shared dataclasses
├── frontend/            # React app (Vite + TypeScript)
└── .env                 # Local config (gitignored)
```

---

## v0.1

- Phoenix and LangSmith adapters
- Two-tier analysis engine (Tier 1 direct, Tier 2 agentic)
- Trace list with status filter and live search
- Per-trace diagnostics: root cause, categorized issues, recommended fixes
- Debug chat per trace
- Settings modal with live connection test
- Analysis result caching
- Project-level P50/P99 latency stats
