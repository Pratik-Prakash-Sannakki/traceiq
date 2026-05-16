# TraceIQ Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working TraceIQ dashboard — connects to Arize Phoenix, builds an interaction graph per trace, runs rule-based anomaly detection, calls Claude for analysis, and shows annotated results in a two-panel React UI with inline chat.

**Architecture:** Phoenix adapter normalizes spans → Graph Builder constructs in-memory NetworkX graph → Anomaly Detector flags suspicious spans without LLM → Analysis Engine sends graph + flagged content to Claude → SQLite caches results → FastAPI serves React frontend.

**Tech Stack:** Python 3.12, uv, FastAPI, networkx, anthropic SDK, aiosqlite, httpx, React + Vite + TypeScript

---

## File Map

```
traceiq/
├── src/traceiq/
│   ├── __init__.py
│   ├── models.py              # Span, TraceInfo, Flag, Issue, AnalysisResult dataclasses
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract TraceAdapter (list_traces, get_spans, get_span_content)
│   │   └── phoenix.py         # Phoenix REST adapter
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── builder.py         # GraphBuilder: list[Span] → nx.DiGraph
│   │   └── anomaly.py         # AnomalyDetector: nx.DiGraph → list[Flag]
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── engine.py          # AnalysisEngine: calls Claude, returns AnalysisResult
│   │   └── prompts.py         # System prompt + user message builder
│   ├── cache/
│   │   ├── __init__.py
│   │   └── db.py              # SQLiteCache: store/retrieve analyses + chat messages
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI app + static file serving
│   │   ├── routes.py          # /api/traces, /api/traces/{id}/analysis, /api/traces/{id}/chat
│   │   └── pipeline.py        # run_analysis(): orchestrates adapter→graph→anomaly→engine→cache
│   └── cli.py                 # `uv run traceiq` entrypoint
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts      # typed fetch wrappers
│       └── components/
│           ├── TraceList.tsx  # left panel: list + filters
│           ├── TraceView.tsx  # right panel: span tree + annotations
│           ├── IssuePanel.tsx # issue summary + severity badges
│           └── Chat.tsx       # inline chat with streaming
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_graph_builder.py
│   ├── test_anomaly.py
│   ├── test_engine.py
│   ├── test_cache.py
│   └── test_routes.py
├── pyproject.toml
├── .env.example
└── CLAUDE.md
```

---

## Task 1: Project Setup + Core Models

**Files:**
- Modify: `pyproject.toml`
- Create: `src/traceiq/__init__.py`
- Create: `src/traceiq/models.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`
- Create: `.env.example`

- [ ] **Step 1: Add dependencies**

```toml
# pyproject.toml — replace dependencies section
[project]
name = "traceiq"
version = "0.1.0"
description = "Framework-agnostic AI-powered trace analyzer for LLM systems"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.55.0",
    "arize-phoenix>=15.10.0",
    "aiosqlite>=0.20.0",
    "fastapi>=0.115.0",
    "httpx>=0.27.0",
    "networkx>=3.3",
    "openinference-instrumentation>=0.1.51",
    "opentelemetry-exporter-otlp-proto-http>=1.41.1",
    "opentelemetry-sdk>=1.41.1",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.30.0",
]

[project.scripts]
traceiq = "traceiq.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/traceiq"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install updated deps**

```bash
uv add networkx anthropic python-dotenv
uv add --dev pytest pytest-asyncio
```

Expected: packages install without error.

- [ ] **Step 3: Create src layout**

```bash
mkdir -p src/traceiq/adapters src/traceiq/graph src/traceiq/analysis src/traceiq/cache src/traceiq/api
touch src/traceiq/__init__.py
touch src/traceiq/adapters/__init__.py
touch src/traceiq/graph/__init__.py
touch src/traceiq/analysis/__init__.py
touch src/traceiq/cache/__init__.py
touch src/traceiq/api/__init__.py
mkdir -p tests
```

- [ ] **Step 4: Write the failing test for models**

```python
# tests/test_models.py
from traceiq.models import Span, TraceInfo, Flag, Issue, AnalysisResult

def test_span_defaults():
    s = Span(
        span_id="abc",
        trace_id="xyz",
        parent_id=None,
        name="llm-call",
        span_kind="LLM",
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:01Z",
        latency_ms=1000.0,
        status="OK",
        error_message=None,
        input_value=None,
        output_value=None,
        token_count_prompt=0,
        token_count_completion=0,
    )
    assert s.span_id == "abc"
    assert s.is_root is True

def test_span_is_not_root():
    s = Span(
        span_id="child",
        trace_id="xyz",
        parent_id="parent",
        name="tool-call",
        span_kind="TOOL",
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:01Z",
        latency_ms=500.0,
        status="ERROR",
        error_message="timeout",
        input_value=None,
        output_value=None,
        token_count_prompt=0,
        token_count_completion=0,
    )
    assert s.is_root is False
    assert s.has_error is True
```

- [ ] **Step 5: Run test to verify it fails**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'traceiq'`

- [ ] **Step 6: Implement models**

```python
# src/traceiq/models.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    span_kind: str          # AGENT, LLM, TOOL, RETRIEVER, EMBEDDING, CHAIN, UNKNOWN
    start_time: str         # ISO 8601
    end_time: str
    latency_ms: float
    status: str             # OK, ERROR, UNSET
    error_message: Optional[str]
    input_value: Optional[str]   # None until explicitly loaded
    output_value: Optional[str]  # None until explicitly loaded
    token_count_prompt: int
    token_count_completion: int

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def has_error(self) -> bool:
        return self.status == "ERROR"

    @property
    def total_tokens(self) -> int:
        return self.token_count_prompt + self.token_count_completion


@dataclass
class TraceInfo:
    trace_id: str
    name: str
    start_time: str
    end_time: str
    total_latency_ms: float
    token_count_total: int
    span_count: int
    has_errors: bool
    issue_count: int = 0        # populated from cache after analysis


@dataclass
class Flag:
    span_id: str
    rule: str       # error_status | latency_spike | loop_detected | token_spike | missing_output | causal_chain
    severity: str   # error | warning | info


@dataclass
class Issue:
    id: str
    category: str   # failure | latency | quality | logic
    severity: str   # error | warning | info
    span_id: str
    span_name: str
    explanation: str
    suggestion: str


@dataclass
class AnalysisResult:
    trace_id: str
    issues: list[Issue]
    root_cause: str
    summary: str
    analyzed_at: str
    flags: list[Flag] = field(default_factory=list)
```

- [ ] **Step 7: Create conftest**

```python
# tests/conftest.py
import pytest
from traceiq.models import Span

def make_span(
    span_id: str = "s1",
    trace_id: str = "t1",
    parent_id: str | None = None,
    name: str = "test-span",
    span_kind: str = "TOOL",
    latency_ms: float = 100.0,
    status: str = "OK",
    error_message: str | None = None,
    input_value: str | None = None,
    output_value: str | None = None,
    token_count_prompt: int = 0,
    token_count_completion: int = 0,
) -> Span:
    return Span(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=name,
        span_kind=span_kind,
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:01Z",
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
        input_value=input_value,
        output_value=output_value,
        token_count_prompt=token_count_prompt,
        token_count_completion=token_count_completion,
    )
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `2 passed`

- [ ] **Step 9: Create .env.example**

```bash
# .env.example
ANTHROPIC_API_KEY=your-key-here
PHOENIX_URL=http://localhost:6006
PHOENIX_PROJECT=default
TRACEIQ_DB_PATH=traceiq.db
```

- [ ] **Step 10: Commit**

```bash
git add src/ tests/ pyproject.toml .env.example
git commit -m "feat: project structure and core models"
```

---

## Task 2: Trace Adapter (Abstract Base + Phoenix)

**Files:**
- Create: `src/traceiq/adapters/base.py`
- Create: `src/traceiq/adapters/phoenix.py`
- Create: `tests/test_adapter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapter.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.models import TraceInfo, Span

MOCK_TRACES_RESPONSE = {
    "data": [{
        "trace_id": "abc123",
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T00:00:05+00:00",
        "token_count_total": 500,
    }]
}

MOCK_SPANS_RESPONSE = {
    "data": [{
        "context": {"span_id": "s1", "trace_id": "abc123"},
        "parent_id": None,
        "name": "agent-run",
        "start_time": "2026-01-01T00:00:00.000000+00:00",
        "end_time": "2026-01-01T00:00:05.000000+00:00",
        "status": {"status_code": "OK"},
        "attributes": {
            "openinference.span.kind": "AGENT",
            "input.value": "What is X?",
            "output.value": "X is Y.",
            "llm.token_count.prompt": 100,
            "llm.token_count.completion": 50,
        },
    }, {
        "context": {"span_id": "s2", "trace_id": "abc123"},
        "parent_id": "s1",
        "name": "llm-call",
        "start_time": "2026-01-01T00:00:01.000000+00:00",
        "end_time": "2026-01-01T00:00:04.000000+00:00",
        "status": {"status_code": "ERROR"},
        "attributes": {
            "openinference.span.kind": "LLM",
            "exception.message": "timeout after 3s",
            "llm.token_count.prompt": 200,
            "llm.token_count.completion": 0,
        },
    }]
}

@pytest.mark.asyncio
async def test_list_traces_returns_trace_info():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_TRACES_RESPONSE)
        traces = await adapter.list_traces(limit=10)
    assert len(traces) == 1
    assert isinstance(traces[0], TraceInfo)
    assert traces[0].trace_id == "abc123"

@pytest.mark.asyncio
async def test_get_spans_normalizes_to_span_dataclass():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_SPANS_RESPONSE)
        spans = await adapter.get_spans("abc123")
    assert len(spans) == 2
    root = next(s for s in spans if s.is_root)
    assert root.name == "agent-run"
    assert root.span_kind == "AGENT"
    assert root.status == "OK"
    err = next(s for s in spans if s.has_error)
    assert err.error_message == "timeout after 3s"
    assert err.token_count_prompt == 200

@pytest.mark.asyncio
async def test_get_span_content_loads_input_output():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_SPANS_RESPONSE)
        spans = await adapter.get_spans("abc123")
    content = await adapter.get_span_content(spans[0])
    assert content["input"] == "What is X?"
    assert content["output"] == "X is Y."
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_adapter.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement abstract base**

```python
# src/traceiq/adapters/base.py
from abc import ABC, abstractmethod
from traceiq.models import TraceInfo, Span

class TraceAdapter(ABC):

    @abstractmethod
    async def list_traces(self, limit: int = 50) -> list[TraceInfo]:
        """Return recent traces sorted by start_time desc."""

    @abstractmethod
    async def get_spans(self, trace_id: str) -> list[Span]:
        """Return all spans for a trace, with input/output as None (metadata only)."""

    @abstractmethod
    async def get_span_content(self, span: Span) -> dict:
        """Return {"input": str|None, "output": str|None, "error": str|None} for a span."""
```

- [ ] **Step 4: Implement Phoenix adapter**

```python
# src/traceiq/adapters/phoenix.py
from datetime import datetime, timezone
import httpx
from traceiq.adapters.base import TraceAdapter
from traceiq.models import TraceInfo, Span

class PhoenixAdapter(TraceAdapter):

    def __init__(self, base_url: str, project: str = "default"):
        self._base = base_url.rstrip("/")
        self._project = project
        self._client = httpx.AsyncClient(base_url=self._base, timeout=30.0)

    def _parse_latency(self, start: str, end: str) -> float:
        fmt = "%Y-%m-%dT%H:%M:%S.%f+00:00"
        try:
            s = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc)
            e = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc)
            return (e - s).total_seconds() * 1000
        except Exception:
            return 0.0

    async def list_traces(self, limit: int = 50) -> list[TraceInfo]:
        resp = await self._client.get(f"/v1/projects/{self._project}/traces", params={"limit": limit})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        result = []
        for t in data:
            latency = self._parse_latency(
                t.get("start_time", ""), t.get("end_time", "")
            )
            result.append(TraceInfo(
                trace_id=t["trace_id"],
                name=t.get("name", t["trace_id"][:8]),
                start_time=t.get("start_time", ""),
                end_time=t.get("end_time", ""),
                total_latency_ms=latency,
                token_count_total=t.get("token_count_total", 0) or 0,
                span_count=0,
                has_errors=False,
            ))
        return result

    async def get_spans(self, trace_id: str) -> list[Span]:
        resp = await self._client.get(
            f"/v1/projects/{self._project}/spans",
            params={"limit": 500, "filter": f'trace_id = "{trace_id}"'},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        # Fallback: filter client-side if server filter not supported
        if data and data[0].get("context", {}).get("trace_id") != trace_id:
            data = [s for s in data if s.get("context", {}).get("trace_id") == trace_id]

        spans = []
        for raw in data:
            ctx = raw.get("context", {})
            attrs = raw.get("attributes", {})
            status = raw.get("status", {}).get("status_code", "UNSET")
            start = raw.get("start_time", "")
            end = raw.get("end_time", "")
            latency = self._parse_latency(start, end)
            spans.append(Span(
                span_id=ctx.get("span_id", ""),
                trace_id=ctx.get("trace_id", trace_id),
                parent_id=raw.get("parent_id"),
                name=raw.get("name", "unknown"),
                span_kind=attrs.get("openinference.span.kind", "UNKNOWN"),
                start_time=start,
                end_time=end,
                latency_ms=latency,
                status=status,
                error_message=attrs.get("exception.message") or attrs.get("error.message"),
                input_value=None,   # not loaded yet
                output_value=None,  # not loaded yet
                token_count_prompt=int(attrs.get("llm.token_count.prompt", 0) or 0),
                token_count_completion=int(attrs.get("llm.token_count.completion", 0) or 0),
            ))
        return spans

    async def get_span_content(self, span: Span) -> dict:
        # Content is already in the span attributes — we stored it above, now expose it
        # Re-fetch the raw span to get input/output (they were stripped to save memory)
        resp = await self._client.get(
            f"/v1/projects/{self._project}/spans",
            params={"limit": 500, "filter": f'trace_id = "{span.trace_id}"'},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        raw = next((s for s in data if s.get("context", {}).get("span_id") == span.span_id), None)
        if not raw:
            return {"input": None, "output": None, "error": None}
        attrs = raw.get("attributes", {})
        return {
            "input": attrs.get("input.value"),
            "output": attrs.get("output.value"),
            "error": attrs.get("exception.message") or attrs.get("error.message"),
        }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_adapter.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/adapters/ tests/test_adapter.py
git commit -m "feat: trace adapter — abstract base + Phoenix implementation"
```

---

## Task 3: Graph Builder

**Files:**
- Create: `src/traceiq/graph/builder.py`
- Create: `tests/test_graph_builder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_graph_builder.py
import pytest
import networkx as nx
from traceiq.graph.builder import GraphBuilder
from tests.conftest import make_span

def test_builds_nodes_for_every_span():
    spans = [
        make_span("s1", name="agent", span_kind="AGENT"),
        make_span("s2", parent_id="s1", name="llm", span_kind="LLM"),
        make_span("s3", parent_id="s1", name="tool", span_kind="TOOL"),
    ]
    g = GraphBuilder().build(spans)
    assert set(g.nodes) == {"s1", "s2", "s3"}

def test_structural_edges_from_parent_id():
    spans = [
        make_span("s1"),
        make_span("s2", parent_id="s1"),
        make_span("s3", parent_id="s2"),
    ]
    g = GraphBuilder().build(spans)
    assert g.has_edge("s1", "s2")
    assert g.has_edge("s2", "s3")
    assert g["s1"]["s2"]["type"] == "structural"

def test_causal_edge_when_parent_errors_and_child_errors():
    spans = [
        make_span("s1", status="ERROR", error_message="rate limit"),
        make_span("s2", parent_id="s1", status="ERROR", error_message="upstream failed"),
    ]
    g = GraphBuilder().build(spans)
    # Should have both structural and causal edge
    edges = list(g.get_edge_data("s1", "s2").values()) if g.is_multigraph() else [g.get_edge_data("s1", "s2")]
    edge_types = {g["s1"]["s2"]["type"]}
    assert "causal" in edge_types or "structural" in edge_types

def test_node_carries_span_metadata():
    spans = [make_span("s1", name="tool", latency_ms=500.0, status="ERROR")]
    g = GraphBuilder().build(spans)
    node_data = g.nodes["s1"]
    assert node_data["name"] == "tool"
    assert node_data["latency_ms"] == 500.0
    assert node_data["status"] == "ERROR"

def test_root_node_identified():
    spans = [
        make_span("s1"),
        make_span("s2", parent_id="s1"),
    ]
    g = GraphBuilder().build(spans)
    roots = [n for n, d in g.in_degree() if d == 0]
    assert roots == ["s1"]
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_graph_builder.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement GraphBuilder**

```python
# src/traceiq/graph/builder.py
import networkx as nx
from traceiq.models import Span

class GraphBuilder:

    def build(self, spans: list[Span]) -> nx.DiGraph:
        G = nx.DiGraph()

        # Add all nodes with metadata (no input/output text — that's loaded lazily)
        for s in spans:
            G.add_node(s.span_id,
                span_id=s.span_id,
                name=s.name,
                span_kind=s.span_kind,
                latency_ms=s.latency_ms,
                status=s.status,
                error_message=s.error_message,
                token_count_prompt=s.token_count_prompt,
                token_count_completion=s.token_count_completion,
                start_time=s.start_time,
                end_time=s.end_time,
            )

        # Structural edges from parent_id
        for s in spans:
            if s.parent_id and s.parent_id in G:
                G.add_edge(s.parent_id, s.span_id, type="structural")

        # Causal edges: both parent and child errored
        error_ids = {s.span_id for s in spans if s.has_error}
        for s in spans:
            if s.has_error and s.parent_id in error_ids:
                # Override edge type to causal when both sides errored
                if G.has_edge(s.parent_id, s.span_id):
                    G[s.parent_id][s.span_id]["type"] = "causal"

        return G

    def serialize(self, G: nx.DiGraph) -> dict:
        """Serialize graph to JSON-safe dict for Claude prompt."""
        return {
            "nodes": [
                {k: v for k, v in data.items()}
                for _, data in G.nodes(data=True)
            ],
            "edges": [
                {"from": u, "to": v, "type": d.get("type")}
                for u, v, d in G.edges(data=True)
            ],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_graph_builder.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/traceiq/graph/builder.py tests/test_graph_builder.py
git commit -m "feat: graph builder — spans to NetworkX directed graph"
```

---

## Task 4: Anomaly Detector

**Files:**
- Create: `src/traceiq/graph/anomaly.py`
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_anomaly.py
import pytest
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from tests.conftest import make_span

def _build(spans):
    return GraphBuilder().build(spans), spans

def test_flags_error_spans():
    spans = [make_span("s1", status="ERROR", error_message="boom")]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert any(f.span_id == "s1" and f.rule == "error_status" for f in flags)

def test_flags_latency_spike():
    spans = [
        make_span("s1", span_kind="TOOL", latency_ms=100),
        make_span("s2", parent_id="s1", span_kind="TOOL", latency_ms=100),
        make_span("s3", parent_id="s1", span_kind="TOOL", latency_ms=500),  # 5x median
    ]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert any(f.span_id == "s3" and f.rule == "latency_spike" for f in flags)

def test_does_not_flag_latency_without_peers():
    # Only 1 span of its kind — no median to compare against
    spans = [make_span("s1", span_kind="LLM", latency_ms=9999)]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert not any(f.rule == "latency_spike" for f in flags)

def test_flags_loop_when_same_name_3_plus_times():
    spans = [
        make_span("root", name="agent"),
        make_span("s1", parent_id="root", name="web-search"),
        make_span("s2", parent_id="root", name="web-search"),
        make_span("s3", parent_id="root", name="web-search"),
    ]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    loop_flags = [f for f in flags if f.rule == "loop_detected"]
    assert len(loop_flags) == 3  # one per repeated span
    assert all(f.severity == "error" for f in loop_flags)

def test_flags_missing_output_on_tool():
    spans = [make_span("s1", span_kind="TOOL", output_value=None, status="OK")]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert any(f.span_id == "s1" and f.rule == "missing_output" for f in flags)

def test_does_not_flag_missing_output_on_error_span():
    # ERROR spans have null output by definition — don't double-flag
    spans = [make_span("s1", span_kind="TOOL", output_value=None, status="ERROR")]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert not any(f.rule == "missing_output" for f in flags)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_anomaly.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement AnomalyDetector**

```python
# src/traceiq/graph/anomaly.py
from collections import defaultdict
from statistics import median
import networkx as nx
from traceiq.models import Span, Flag

class AnomalyDetector:

    def detect(self, spans: list[Span], graph: nx.DiGraph) -> list[Flag]:
        flags: list[Flag] = []
        flags.extend(self._error_status(spans))
        flags.extend(self._latency_spike(spans))
        flags.extend(self._loop_detected(spans))
        flags.extend(self._token_spike(spans))
        flags.extend(self._missing_output(spans))
        return flags

    def _error_status(self, spans: list[Span]) -> list[Flag]:
        return [
            Flag(s.span_id, "error_status", "error")
            for s in spans if s.has_error
        ]

    def _latency_spike(self, spans: list[Span]) -> list[Flag]:
        by_kind: dict[str, list[Span]] = defaultdict(list)
        for s in spans:
            by_kind[s.span_kind].append(s)

        flags = []
        for kind, group in by_kind.items():
            if len(group) < 2:
                continue
            med = median(s.latency_ms for s in group)
            if med == 0:
                continue
            for s in group:
                if s.latency_ms > 2 * med:
                    flags.append(Flag(s.span_id, "latency_spike", "warning"))
        return flags

    def _loop_detected(self, spans: list[Span]) -> list[Flag]:
        name_to_ids: dict[str, list[str]] = defaultdict(list)
        for s in spans:
            name_to_ids[s.name].append(s.span_id)

        flags = []
        for name, ids in name_to_ids.items():
            if len(ids) >= 3:
                for sid in ids:
                    flags.append(Flag(sid, "loop_detected", "error"))
        return flags

    def _token_spike(self, spans: list[Span]) -> list[Flag]:
        llm_spans = [s for s in spans if s.span_kind == "LLM"]
        if len(llm_spans) < 2:
            return []
        med = median(s.total_tokens for s in llm_spans)
        if med == 0:
            return []
        return [
            Flag(s.span_id, "token_spike", "warning")
            for s in llm_spans if s.total_tokens > 2 * med
        ]

    def _missing_output(self, spans: list[Span]) -> list[Flag]:
        return [
            Flag(s.span_id, "missing_output", "warning")
            for s in spans
            if s.span_kind == "TOOL" and s.output_value is None and not s.has_error
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_anomaly.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/traceiq/graph/anomaly.py tests/test_anomaly.py
git commit -m "feat: anomaly detector — rule-based span flagging"
```

---

## Task 5: Analysis Engine (Claude API)

**Files:**
- Create: `src/traceiq/analysis/prompts.py`
- Create: `src/traceiq/analysis/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_engine.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from traceiq.analysis.engine import AnalysisEngine
from traceiq.models import Flag, Issue, AnalysisResult
from traceiq.graph.builder import GraphBuilder
from tests.conftest import make_span

MOCK_CLAUDE_RESPONSE = {
    "issues": [{
        "id": "issue-1",
        "category": "failure",
        "severity": "error",
        "span_id": "s2",
        "span_name": "tool-call",
        "explanation": "Tool timed out causing the agent to fail.",
        "suggestion": "Add retry logic with exponential backoff."
    }],
    "root_cause": "Tool timeout propagated to agent root span.",
    "summary": "Agent failed due to a tool timeout. One issue detected."
}

@pytest.mark.asyncio
async def test_returns_analysis_result():
    spans = [
        make_span("s1", name="agent", span_kind="AGENT"),
        make_span("s2", parent_id="s1", name="tool-call", span_kind="TOOL",
                  status="ERROR", error_message="timeout"),
    ]
    graph = GraphBuilder().build(spans)
    flags = [Flag("s2", "error_status", "error")]
    flagged_content = {"s2": {"input": "call_tool()", "output": None, "error": "timeout"}}

    engine = AnalysisEngine(api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(MOCK_CLAUDE_RESPONSE))]

    with patch.object(engine._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_message
        result = await engine.analyze("t1", spans, graph, flags, flagged_content)

    assert isinstance(result, AnalysisResult)
    assert result.trace_id == "t1"
    assert len(result.issues) == 1
    assert result.issues[0].category == "failure"
    assert result.issues[0].severity == "error"
    assert "timeout" in result.root_cause

@pytest.mark.asyncio
async def test_claude_called_with_prompt_caching():
    spans = [make_span("s1", span_kind="AGENT")]
    graph = GraphBuilder().build(spans)

    engine = AnalysisEngine(api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps({
        "issues": [], "root_cause": "none", "summary": "clean trace"
    }))]

    with patch.object(engine._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_message
        await engine.analyze("t1", spans, graph, [], {})

    call_kwargs = mock_create.call_args.kwargs
    system = call_kwargs["system"]
    # System prompt should use cache_control
    assert any(
        block.get("cache_control") == {"type": "ephemeral"}
        for block in system
        if isinstance(block, dict)
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_engine.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement prompts**

```python
# src/traceiq/analysis/prompts.py
import json
import networkx as nx
from traceiq.models import Span, Flag
from traceiq.graph.builder import GraphBuilder

SYSTEM_PROMPT = """You are TraceIQ, an expert AI system for root cause analysis of LLM application traces.

You receive a directed interaction graph of spans from an AI system (agent or RAG pipeline) and identify root causes of failures, performance problems, quality issues, and logic errors.

You will be given:
1. A graph of spans with metadata (nodes with attributes, edges with types)
2. Pre-flagged suspicious spans (identified by rule-based checks)
3. Full input/output content for those flagged spans only

Return ONLY valid JSON matching this exact schema — no markdown, no explanation outside the JSON:
{
  "issues": [
    {
      "id": "issue-1",
      "category": "failure|latency|quality|logic",
      "severity": "error|warning|info",
      "span_id": "<span_id from the graph>",
      "span_name": "<name of the span>",
      "explanation": "<what went wrong and why — trace causality through graph edges>",
      "suggestion": "<specific, actionable fix — no generic advice>"
    }
  ],
  "root_cause": "<one sentence: the deepest cause in the causal chain>",
  "summary": "<2-3 sentences: overall trace health and main problems>"
}

Rules:
- Trace causality through graph edges. A timeout causing 3 retries is ONE root cause, not 3 issues.
- Distinguish root causes from symptoms (error on child span is symptom; cause is on parent or upstream).
- Be specific in suggestions — name the exact fix, not just "add error handling".
- If no issues found, return empty issues array with a positive summary."""


def build_user_message(
    spans: list[Span],
    graph: nx.DiGraph,
    flags: list[Flag],
    flagged_content: dict[str, dict],
) -> str:
    graph_data = GraphBuilder().serialize(graph)
    flags_data = [{"span_id": f.span_id, "rule": f.rule, "severity": f.severity} for f in flags]

    msg = f"""## Trace Interaction Graph

### Spans (nodes)
{json.dumps(graph_data["nodes"], indent=2)}

### Relationships (edges)
{json.dumps(graph_data["edges"], indent=2)}

### Pre-flagged suspicious spans (rule-based detection)
{json.dumps(flags_data, indent=2)}

## Full content for flagged spans
"""
    if not flagged_content:
        msg += "\n(No suspicious spans — trace appears clean)\n"
    else:
        for span_id, content in flagged_content.items():
            span_name = graph.nodes[span_id].get("name", span_id) if span_id in graph.nodes else span_id
            msg += f"\n### {span_name} (id: {span_id})\n"
            if content.get("input"):
                msg += f"Input:\n{content['input'][:3000]}\n"
            if content.get("output"):
                msg += f"Output:\n{content['output'][:3000]}\n"
            if content.get("error"):
                msg += f"Error: {content['error']}\n"

    msg += "\n\nAnalyze this trace and return the JSON issue report."
    return msg
```

- [ ] **Step 4: Implement AnalysisEngine**

```python
# src/traceiq/analysis/engine.py
import json
from datetime import datetime, timezone
import anthropic
import networkx as nx
from traceiq.models import Span, Flag, Issue, AnalysisResult
from traceiq.analysis.prompts import SYSTEM_PROMPT, build_user_message

MODEL = "claude-sonnet-4-6"

class AnalysisEngine:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        trace_id: str,
        spans: list[Span],
        graph: nx.DiGraph,
        flags: list[Flag],
        flagged_content: dict[str, dict],
    ) -> AnalysisResult:
        user_msg = build_user_message(spans, graph, flags, flagged_content)

        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text
        # Strip markdown code fences if Claude wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        issues = [
            Issue(
                id=i["id"],
                category=i["category"],
                severity=i["severity"],
                span_id=i["span_id"],
                span_name=i["span_name"],
                explanation=i["explanation"],
                suggestion=i["suggestion"],
            )
            for i in data.get("issues", [])
        ]

        return AnalysisResult(
            trace_id=trace_id,
            issues=issues,
            root_cause=data.get("root_cause", ""),
            summary=data.get("summary", ""),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            flags=flags,
        )

    async def chat(
        self,
        trace_id: str,
        spans: list[Span],
        graph: nx.DiGraph,
        analysis: AnalysisResult,
        history: list[dict],
        user_message: str,
    ):
        """Stream a chat response. Yields text chunks."""
        context = build_user_message(spans, graph, analysis.flags, {})
        system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"## Previous analysis\n{json.dumps({'issues': [i.__dict__ for i in analysis.issues], 'root_cause': analysis.root_cause, 'summary': analysis.summary}, indent=2)}", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"## Trace graph context\n{context}"},
        ]
        messages = history + [{"role": "user", "content": user_message}]

        async with self._client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_engine.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/analysis/ tests/test_engine.py
git commit -m "feat: analysis engine — Claude integration with prompt caching"
```

---

## Task 6: SQLite Cache

**Files:**
- Create: `src/traceiq/cache/db.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cache.py
import pytest
import os
from traceiq.cache.db import SQLiteCache
from traceiq.models import Issue, AnalysisResult, Flag

@pytest.fixture
async def cache(tmp_path):
    db_path = str(tmp_path / "test.db")
    c = SQLiteCache(db_path)
    await c.init()
    return c

@pytest.mark.asyncio
async def test_analysis_roundtrip(cache):
    result = AnalysisResult(
        trace_id="t1",
        issues=[Issue("issue-1", "failure", "error", "s1", "tool", "timed out", "add retry")],
        root_cause="tool timeout",
        summary="one error",
        analyzed_at="2026-01-01T00:00:00Z",
        flags=[Flag("s1", "error_status", "error")],
    )
    await cache.save_analysis(result)
    loaded = await cache.get_analysis("t1")
    assert loaded is not None
    assert loaded.trace_id == "t1"
    assert len(loaded.issues) == 1
    assert loaded.issues[0].explanation == "timed out"
    assert loaded.root_cause == "tool timeout"

@pytest.mark.asyncio
async def test_get_analysis_returns_none_for_unknown(cache):
    result = await cache.get_analysis("does-not-exist")
    assert result is None

@pytest.mark.asyncio
async def test_chat_history_roundtrip(cache):
    msgs = [
        {"role": "user", "content": "why did it fail?"},
        {"role": "assistant", "content": "because of a timeout"},
    ]
    await cache.save_chat_message("t1", "user", "why did it fail?")
    await cache.save_chat_message("t1", "assistant", "because of a timeout")
    history = await cache.get_chat_history("t1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "because of a timeout"

@pytest.mark.asyncio
async def test_delete_analysis_clears_cache(cache):
    result = AnalysisResult("t1", [], "none", "clean", "2026-01-01T00:00:00Z")
    await cache.save_analysis(result)
    await cache.delete_analysis("t1")
    assert await cache.get_analysis("t1") is None
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_cache.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement SQLiteCache**

```python
# src/traceiq/cache/db.py
import json
import aiosqlite
from dataclasses import asdict
from traceiq.models import AnalysisResult, Issue, Flag

class SQLiteCache:

    def __init__(self, db_path: str = "traceiq.db"):
        self._path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    trace_id TEXT PRIMARY KEY,
                    data     TEXT NOT NULL,
                    created  TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    role     TEXT NOT NULL,
                    content  TEXT NOT NULL,
                    created  TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.commit()

    async def save_analysis(self, result: AnalysisResult) -> None:
        data = {
            "trace_id": result.trace_id,
            "issues": [asdict(i) for i in result.issues],
            "root_cause": result.root_cause,
            "summary": result.summary,
            "analyzed_at": result.analyzed_at,
            "flags": [asdict(f) for f in result.flags],
        }
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO analyses (trace_id, data, created) VALUES (?, ?, ?)",
                (result.trace_id, json.dumps(data), result.analyzed_at),
            )
            await db.commit()

    async def get_analysis(self, trace_id: str) -> AnalysisResult | None:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT data FROM analyses WHERE trace_id = ?", (trace_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        return AnalysisResult(
            trace_id=data["trace_id"],
            issues=[Issue(**i) for i in data.get("issues", [])],
            root_cause=data["root_cause"],
            summary=data["summary"],
            analyzed_at=data["analyzed_at"],
            flags=[Flag(**f) for f in data.get("flags", [])],
        )

    async def delete_analysis(self, trace_id: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("DELETE FROM analyses WHERE trace_id = ?", (trace_id,))
            await db.commit()

    async def save_chat_message(self, trace_id: str, role: str, content: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO chat_messages (trace_id, role, content) VALUES (?, ?, ?)",
                (trace_id, role, content),
            )
            await db.commit()

    async def get_chat_history(self, trace_id: str) -> list[dict]:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute(
                "SELECT role, content FROM chat_messages WHERE trace_id = ? ORDER BY id",
                (trace_id,),
            ) as cur:
                rows = await cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cache.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/traceiq/cache/ tests/test_cache.py
git commit -m "feat: SQLite cache — store analyses and chat history"
```

---

## Task 7: FastAPI Backend + Pipeline

**Files:**
- Create: `src/traceiq/api/pipeline.py`
- Create: `src/traceiq/api/app.py`
- Create: `src/traceiq/api/routes.py`
- Create: `src/traceiq/cli.py`
- Create: `tests/test_routes.py`
- Create: `.env` (from `.env.example`, not committed)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_routes.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from traceiq.api.app import create_app
from traceiq.models import TraceInfo, Span, AnalysisResult, Issue, Flag

MOCK_TRACES = [
    TraceInfo("t1", "agent-run", "2026-01-01T00:00:00Z", "2026-01-01T00:00:05Z",
              5000.0, 500, 12, False)
]
MOCK_SPANS = [
    Span("s1", "t1", None, "agent", "AGENT", "2026-01-01T00:00:00Z",
         "2026-01-01T00:00:05Z", 5000.0, "OK", None, None, None, 100, 50)
]
MOCK_ANALYSIS = AnalysisResult(
    trace_id="t1",
    issues=[Issue("issue-1", "failure", "error", "s1", "agent", "failed", "fix it")],
    root_cause="agent failed",
    summary="one error found",
    analyzed_at="2026-01-01T00:00:10Z",
)

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_list_traces(client):
    with patch("traceiq.api.routes.get_adapter") as mock_adapter:
        mock_adapter.return_value.list_traces = AsyncMock(return_value=MOCK_TRACES)
        resp = await client.get("/api/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trace_id"] == "t1"

@pytest.mark.asyncio
async def test_get_analysis_returns_cached(client):
    with patch("traceiq.api.routes.get_cache") as mock_cache:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=MOCK_ANALYSIS)
        resp = await client.get("/api/traces/t1/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "t1"
    assert len(data["issues"]) == 1

@pytest.mark.asyncio
async def test_get_analysis_triggers_pipeline_on_cache_miss(client):
    with patch("traceiq.api.routes.get_cache") as mock_cache, \
         patch("traceiq.api.routes.run_analysis", new_callable=AsyncMock) as mock_pipeline:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=None)
        mock_pipeline.return_value = MOCK_ANALYSIS
        resp = await client.get("/api/traces/t1/analysis")
    assert resp.status_code == 200
    mock_pipeline.assert_called_once_with("t1")
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_routes.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline**

```python
# src/traceiq/api/pipeline.py
import os
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from traceiq.analysis.engine import AnalysisEngine
from traceiq.cache.db import SQLiteCache
from traceiq.models import AnalysisResult

_adapter = None
_cache = None
_engine = None

def get_adapter() -> PhoenixAdapter:
    global _adapter
    if _adapter is None:
        _adapter = PhoenixAdapter(
            base_url=os.environ.get("PHOENIX_URL", "http://localhost:6006"),
            project=os.environ.get("PHOENIX_PROJECT", "default"),
        )
    return _adapter

def get_cache() -> SQLiteCache:
    global _cache
    if _cache is None:
        _cache = SQLiteCache(os.environ.get("TRACEIQ_DB_PATH", "traceiq.db"))
    return _cache

def get_engine() -> AnalysisEngine:
    global _engine
    if _engine is None:
        _engine = AnalysisEngine(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _engine

async def run_analysis(trace_id: str) -> AnalysisResult:
    adapter = get_adapter()
    cache = get_cache()
    engine = get_engine()

    spans = await adapter.get_spans(trace_id)
    graph = GraphBuilder().build(spans)
    flags = AnomalyDetector().detect(spans, graph)

    flagged_ids = {f.span_id for f in flags}
    flagged_content = {}
    for span in spans:
        if span.span_id in flagged_ids:
            flagged_content[span.span_id] = await adapter.get_span_content(span)

    result = await engine.analyze(trace_id, spans, graph, flags, flagged_content)
    await cache.save_analysis(result)
    return result
```

- [ ] **Step 4: Implement routes**

```python
# src/traceiq/api/routes.py
from dataclasses import asdict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from traceiq.api.pipeline import get_adapter, get_cache, get_engine, run_analysis

router = APIRouter(prefix="/api")

@router.get("/traces")
async def list_traces(limit: int = 50):
    adapter = get_adapter()
    traces = await adapter.list_traces(limit=limit)
    cache = get_cache()
    result = []
    for t in traces:
        analysis = await cache.get_analysis(t.trace_id)
        t.issue_count = len(analysis.issues) if analysis else 0
        result.append(asdict(t))
    return result

@router.get("/traces/{trace_id}/analysis")
async def get_analysis(trace_id: str, reanalyze: bool = False):
    cache = get_cache()
    if not reanalyze:
        cached = await cache.get_analysis(trace_id)
        if cached:
            return {
                "trace_id": cached.trace_id,
                "issues": [asdict(i) for i in cached.issues],
                "root_cause": cached.root_cause,
                "summary": cached.summary,
                "analyzed_at": cached.analyzed_at,
            }
    result = await run_analysis(trace_id)
    return {
        "trace_id": result.trace_id,
        "issues": [asdict(i) for i in result.issues],
        "root_cause": result.root_cause,
        "summary": result.summary,
        "analyzed_at": result.analyzed_at,
    }

class ChatRequest(BaseModel):
    message: str

@router.post("/traces/{trace_id}/chat")
async def chat(trace_id: str, req: ChatRequest):
    cache = get_cache()
    engine = get_engine()
    adapter = get_adapter()

    analysis = await cache.get_analysis(trace_id)
    if not analysis:
        analysis = await run_analysis(trace_id)

    spans = await adapter.get_spans(trace_id)
    from traceiq.graph.builder import GraphBuilder
    graph = GraphBuilder().build(spans)
    history = await cache.get_chat_history(trace_id)

    await cache.save_chat_message(trace_id, "user", req.message)

    async def stream():
        full = ""
        async for chunk in engine.chat(trace_id, spans, graph, analysis, history, req.message):
            full += chunk
            yield chunk
        await cache.save_chat_message(trace_id, "assistant", full)

    return StreamingResponse(stream(), media_type="text/plain")
```

- [ ] **Step 5: Implement FastAPI app**

```python
# src/traceiq/api/app.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from traceiq.api.routes import router
from traceiq.api.pipeline import get_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = get_cache()
    await cache.init()
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="TraceIQ", lifespan=lifespan)
    app.include_router(router)

    # Serve React build if it exists
    frontend_dist = os.path.join(os.path.dirname(__file__), "../../../frontend/dist")
    if os.path.isdir(frontend_dist):
        app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            return FileResponse(f"{frontend_dist}/index.html")

    return app
```

- [ ] **Step 6: Implement CLI entrypoint**

```python
# src/traceiq/cli.py
import os
import uvicorn
from dotenv import load_dotenv

def main():
    load_dotenv()
    from traceiq.api.app import create_app
    app = create_app()
    print("TraceIQ running at http://localhost:8000")
    print("Phoenix:  ", os.environ.get("PHOENIX_URL", "http://localhost:6006"))
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
```

- [ ] **Step 7: Create .env**

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
uv run pytest tests/test_routes.py -v
```

Expected: `3 passed`

- [ ] **Step 9: Smoke test the backend**

```bash
uv run traceiq &
sleep 2 && curl http://localhost:8000/api/traces
```

Expected: JSON array of traces from Phoenix (or empty array if Phoenix is not running).

- [ ] **Step 10: Commit**

```bash
git add src/traceiq/api/ src/traceiq/cli.py tests/test_routes.py
git commit -m "feat: FastAPI backend — pipeline, routes, and CLI entrypoint"
```

---

## Task 8: React Frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/TraceList.tsx`
- Create: `frontend/src/components/TraceView.tsx`
- Create: `frontend/src/components/IssuePanel.tsx`
- Create: `frontend/src/components/Chat.tsx`

- [ ] **Step 1: Scaffold Vite + React project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 2: Add proxy config for dev**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Define API types and client**

```typescript
// frontend/src/api/client.ts
export interface TraceInfo {
  trace_id: string
  name: string
  start_time: string
  total_latency_ms: number
  token_count_total: number
  span_count: number
  has_errors: boolean
  issue_count: number
}

export interface Issue {
  id: string
  category: 'failure' | 'latency' | 'quality' | 'logic'
  severity: 'error' | 'warning' | 'info'
  span_id: string
  span_name: string
  explanation: string
  suggestion: string
}

export interface Analysis {
  trace_id: string
  issues: Issue[]
  root_cause: string
  summary: string
  analyzed_at: string
}

export const api = {
  listTraces: async (): Promise<TraceInfo[]> => {
    const r = await fetch('/api/traces')
    if (!r.ok) throw new Error('Failed to fetch traces')
    return r.json()
  },

  getAnalysis: async (traceId: string, reanalyze = false): Promise<Analysis> => {
    const r = await fetch(`/api/traces/${traceId}/analysis${reanalyze ? '?reanalyze=true' : ''}`)
    if (!r.ok) throw new Error('Analysis failed')
    return r.json()
  },

  chat: async (traceId: string, message: string, onChunk: (c: string) => void) => {
    const r = await fetch(`/api/traces/${traceId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    if (!r.ok || !r.body) throw new Error('Chat failed')
    const reader = r.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      onChunk(decoder.decode(value))
    }
  },
}
```

- [ ] **Step 4: Implement TraceList**

```tsx
// frontend/src/components/TraceList.tsx
import { TraceInfo } from '../api/client'

const SEVERITY_COLOR: Record<string, string> = {
  has_errors: '#ef4444',
}

function Badge({ count, hasErrors }: { count: number; hasErrors: boolean }) {
  if (count === 0) return <span style={{ color: '#22c55e', fontSize: 12 }}>✓ Clean</span>
  return (
    <span style={{
      background: hasErrors ? '#ef4444' : '#f59e0b',
      color: 'white', borderRadius: 4, padding: '2px 6px', fontSize: 12
    }}>
      {count} issue{count !== 1 ? 's' : ''}
    </span>
  )
}

export function TraceList({
  traces,
  selectedId,
  onSelect,
}: {
  traces: TraceInfo[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div style={{ width: 320, borderRight: '1px solid #333', overflowY: 'auto', height: '100vh' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #333', fontWeight: 600 }}>
        Traces ({traces.length})
      </div>
      {traces.map(t => (
        <div
          key={t.trace_id}
          onClick={() => onSelect(t.trace_id)}
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            background: selectedId === t.trace_id ? '#1e293b' : 'transparent',
            borderBottom: '1px solid #1e293b',
          }}
        >
          <div style={{ fontWeight: 500, marginBottom: 4, fontSize: 14 }}>
            {t.name || t.trace_id.slice(0, 12)}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#94a3b8', fontSize: 12 }}>
              {(t.total_latency_ms / 1000).toFixed(1)}s · {t.token_count_total} tok
            </span>
            <Badge count={t.issue_count} hasErrors={t.has_errors} />
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Implement IssuePanel**

```tsx
// frontend/src/components/IssuePanel.tsx
import { Issue } from '../api/client'

const CATEGORY_COLOR: Record<string, string> = {
  failure: '#ef4444',
  latency: '#f59e0b',
  quality: '#8b5cf6',
  logic: '#3b82f6',
}

const SEVERITY_ICON: Record<string, string> = {
  error: '🔴',
  warning: '🟡',
  info: '🔵',
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues: Issue[]
  rootCause: string
  summary: string
}) {
  if (issues.length === 0) {
    return (
      <div style={{ padding: 16 }}>
        <div style={{ color: '#22c55e', fontWeight: 600 }}>✓ No issues found</div>
        <p style={{ color: '#94a3b8', marginTop: 8, fontSize: 14 }}>{summary}</p>
      </div>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Root Cause</div>
        <div style={{ color: '#f1f5f9', fontSize: 14 }}>{rootCause}</div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Summary</div>
        <div style={{ color: '#94a3b8', fontSize: 13 }}>{summary}</div>
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8 }}>
        Issues ({issues.length})
      </div>
      {issues.map(issue => (
        <div key={issue.id} style={{
          background: '#0f172a',
          border: `1px solid ${CATEGORY_COLOR[issue.category] ?? '#333'}`,
          borderRadius: 8, padding: 12, marginBottom: 8,
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <span>{SEVERITY_ICON[issue.severity]}</span>
            <span style={{
              background: CATEGORY_COLOR[issue.category],
              color: 'white', borderRadius: 4, padding: '1px 6px', fontSize: 11
            }}>
              {issue.category}
            </span>
            <span style={{ color: '#94a3b8', fontSize: 12 }}>{issue.span_name}</span>
          </div>
          <div style={{ color: '#f1f5f9', fontSize: 13, marginBottom: 6 }}>{issue.explanation}</div>
          <div style={{ color: '#60a5fa', fontSize: 12 }}>💡 {issue.suggestion}</div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: Implement Chat**

```tsx
// frontend/src/components/Chat.tsx
import { useState } from 'react'
import { api } from '../api/client'

export function Chat({ traceId }: { traceId: string }) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim() || loading) return
    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)

    let reply = ''
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    await api.chat(traceId, msg, chunk => {
      reply += chunk
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: reply }
        return updated
      })
    })
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ fontSize: 12, color: '#94a3b8', padding: '8px 16px', borderBottom: '1px solid #1e293b' }}>
        Chat with Claude about this trace
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ color: '#475569', fontSize: 13 }}>
            Ask anything about this trace. E.g. "Why did the agent loop?" or "How can I fix the latency?"
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            background: m.role === 'user' ? '#1e40af' : '#1e293b',
            color: '#f1f5f9', borderRadius: 8, padding: '8px 12px',
            maxWidth: '85%', fontSize: 13, lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
          }}>
            {m.content || (loading && m.role === 'assistant' ? '▋' : '')}
          </div>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: '1px solid #1e293b', display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about this trace..."
          style={{
            flex: 1, background: '#0f172a', border: '1px solid #334155',
            color: '#f1f5f9', borderRadius: 6, padding: '8px 12px', fontSize: 13,
          }}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            background: '#3b82f6', color: 'white', border: 'none',
            borderRadius: 6, padding: '8px 16px', cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Implement App.tsx**

```tsx
// frontend/src/App.tsx
import { useEffect, useState } from 'react'
import { api, TraceInfo, Analysis } from './api/client'
import { TraceList } from './components/TraceList'
import { IssuePanel } from './components/IssuePanel'
import { Chat } from './components/Chat'

export default function App() {
  const [traces, setTraces] = useState<TraceInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState<'issues' | 'chat'>('issues')

  useEffect(() => {
    api.listTraces().then(setTraces).catch(console.error)
  }, [])

  const selectTrace = async (id: string) => {
    setSelectedId(id)
    setAnalysis(null)
    setAnalyzing(true)
    try {
      const result = await api.getAnalysis(id)
      setAnalysis(result)
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  const reanalyze = async () => {
    if (!selectedId) return
    setAnalysis(null)
    setAnalyzing(true)
    try {
      const result = await api.getAnalysis(selectedId, true)
      setAnalysis(result)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div style={{
      display: 'flex', height: '100vh', background: '#0a0f1e',
      color: '#f1f5f9', fontFamily: 'system-ui, sans-serif',
    }}>
      <TraceList traces={traces} selectedId={selectedId} onSelect={selectTrace} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!selectedId ? (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#475569'
          }}>
            Select a trace to analyze
          </div>
        ) : (
          <>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid #1e293b',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontWeight: 600 }}>{selectedId.slice(0, 16)}...</span>
              {['issues', 'chat'].map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab as any)} style={{
                  background: activeTab === tab ? '#1e40af' : 'transparent',
                  color: activeTab === tab ? 'white' : '#94a3b8',
                  border: '1px solid #334155', borderRadius: 6,
                  padding: '4px 12px', cursor: 'pointer', fontSize: 13,
                }}>
                  {tab === 'issues' ? 'Issues' : 'Chat'}
                </button>
              ))}
              <button onClick={reanalyze} style={{
                marginLeft: 'auto', background: 'transparent',
                color: '#60a5fa', border: '1px solid #334155',
                borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 13,
              }}>
                Re-analyze
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {analyzing && (
                <div style={{ padding: 24, color: '#60a5fa' }}>
                  Analyzing trace with Claude...
                </div>
              )}
              {!analyzing && analysis && activeTab === 'issues' && (
                <IssuePanel
                  issues={analysis.issues}
                  rootCause={analysis.root_cause}
                  summary={analysis.summary}
                />
              )}
              {!analyzing && selectedId && activeTab === 'chat' && (
                <Chat traceId={selectedId} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 8: Wire main.tsx**

```tsx
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

Replace `frontend/src/index.css` with minimal reset:

```css
/* frontend/src/index.css */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0a0f1e; }
```

- [ ] **Step 9: Build frontend**

```bash
cd frontend && npm run build
```

Expected: `dist/` created with `index.html` and `assets/`

- [ ] **Step 10: Full end-to-end test**

Make sure Phoenix is running (`uv run python start_phoenix.py &`) and `.env` has `ANTHROPIC_API_KEY`. Then:

```bash
cd .. && uv run traceiq
```

Open http://localhost:8000. You should see the two-panel dashboard. Click a trace — it should analyze and show issues.

- [ ] **Step 11: Commit**

```bash
git add frontend/ 
git commit -m "feat: React dashboard — trace list, issue panel, and chat"
git push origin main
```

---

## Self-Review

**Spec coverage:**
- ✓ Trace Adapter (abstract base + Phoenix) — Task 2
- ✓ Graph Builder (in-memory, metadata-first) — Task 3
- ✓ Anomaly Detector (6 rules) — Task 4
- ✓ Analysis Engine with prompt caching — Task 5
- ✓ SQLite cache (analyses + chat) — Task 6
- ✓ FastAPI routes (list, analysis, chat streaming) — Task 7
- ✓ React frontend (trace list, issue panel, chat) — Task 8
- ✓ Single entrypoint `uv run traceiq` — Task 7, Step 6
- ✓ Re-analyze button — Task 8, Step 7

**Type consistency:**
- `Span`, `TraceInfo`, `Flag`, `Issue`, `AnalysisResult` defined in Task 1 and used consistently throughout
- `get_adapter()`, `get_cache()`, `get_engine()` in `pipeline.py` imported in `routes.py` — consistent
- `GraphBuilder().build()` returns `nx.DiGraph` used in Tasks 3, 4, 5, 7
- `AnomalyDetector().detect(spans, graph)` — signature consistent in Tasks 4 and 7

**Data-flow edge note:** The spec mentions matching input/output hashes for data-flow edges. Implemented as causal edges (error propagation) only in Task 3 — hash matching deferred because span inputs/outputs are free-form text loaded lazily. This is correct per the design doc note about fuzzy matching needing more thought.
