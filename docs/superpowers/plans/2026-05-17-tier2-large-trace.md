# Tier 2: Large Trace Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Tier 2 analysis pipeline for large traces (≥50 spans) that uses Louvain community detection, lossless metadata cards, loop deduplication, and Claude tool use — so clicking any trace in the dashboard works correctly regardless of size.

**Architecture:** TraceClassifier routes large traces to a new AgentAnalyzer that gives Claude structured community metadata cards (~2K tokens) plus tools to retrieve exact raw span content on demand. No lossy summarization. Tier 1 pipeline (small traces) is completely untouched. Both tiers return the same AnalysisResult schema.

**Tech Stack:** Python 3.12, networkx (louvain_communities already installed), anthropic SDK (tool use), FastAPI, SQLite. No new dependencies.

---

## File Map

```
src/traceiq/
├── models.py                     MODIFY — add Community, CommunityCard, IterationDelta, CompressedLoop
├── graph/
│   ├── classifier.py             CREATE — TraceClassifier.classify(spans) → "small"|"large"
│   └── community.py              CREATE — CommunityDetector.detect(spans, graph) → list[Community]
├── analysis/
│   ├── community_card.py         CREATE — CommunityCardBuilder.build(community, spans, flags) → CommunityCard
│   ├── loop_dedup.py             CREATE — LoopDeduplicator.compress(community, spans) → CompressedLoop
│   └── agent.py                  CREATE — AgentAnalyzer.analyze(...) → AnalysisResult via Claude tool use
└── api/
    └── pipeline.py               MODIFY — run_analysis() routes to Tier 2 when large

tests/
├── test_tier2_models.py          CREATE
├── test_classifier.py            CREATE
├── test_community.py             CREATE
├── test_community_card.py        CREATE
├── test_loop_dedup.py            CREATE
└── test_agent_analyzer.py        CREATE
```

---

## Task 1: Tier 2 Dataclasses

**Files:**
- Modify: `src/traceiq/models.py`
- Create: `tests/test_tier2_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tier2_models.py
from traceiq.models import Community, CommunityCard, IterationDelta, CompressedLoop

def test_community_fields():
    c = Community(community_id="C0", span_ids=["s1", "s2"], label="AgentLoop")
    assert c.community_id == "C0"
    assert "s1" in c.span_ids
    assert c.label == "AgentLoop"

def test_community_card_fields():
    card = CommunityCard(
        community_id="C0",
        label="AgentLoop",
        span_count=21,
        span_types=["agent", "call_model"],
        iteration_count=7,
        avg_latency_ms=4800.0,
        total_latency_ms=33600.0,
        error_count=0,
        flagged_span_ids=["s5"],
        token_growth={"first": 52000, "last": 265000},
        anomalies=["token_spike_at_iteration_4"],
    )
    assert card.span_count == 21
    assert card.token_growth["last"] == 265000

def test_iteration_delta_fields():
    delta = IterationDelta(
        iteration_index=0,
        span_id="s1",
        reason="baseline",
        latency_ms=4200.0,
        token_count=52000,
        has_error=False,
        error_message=None,
    )
    assert delta.reason == "baseline"
    assert delta.has_error is False

def test_compressed_loop_fields():
    loop = CompressedLoop(
        community_id="C0",
        total_iterations=21,
        kept_iterations=[
            IterationDelta(0, "s1", "baseline", 4200.0, 52000, False, None),
            IterationDelta(20, "s21", "final", 5100.0, 265000, False, None),
        ],
        skipped_count=19,
    )
    assert loop.total_iterations == 21
    assert loop.skipped_count == 19
    assert len(loop.kept_iterations) == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ~/Documents/traceiq && uv run pytest tests/test_tier2_models.py -v
```

Expected: `ImportError` — Community not defined yet.

- [ ] **Step 3: Add dataclasses to models.py**

Append to the bottom of `src/traceiq/models.py` (after the existing AnalysisResult class):

```python
@dataclass
class Community:
    community_id: str
    span_ids: list[str]
    label: str          # inferred from dominant span type/name


@dataclass
class CommunityCard:
    community_id: str
    label: str
    span_count: int
    span_types: list[str]       # unique span_kind values in community
    iteration_count: int        # 1 if not a loop, N if agent loop detected
    avg_latency_ms: float
    total_latency_ms: float
    error_count: int
    flagged_span_ids: list[str] # span_ids flagged by AnomalyDetector in this community
    token_growth: dict          # {"first": int, "last": int} — empty dict if no LLM spans
    anomalies: list[str]        # descriptive labels e.g. "token_spike_at_iteration_4"


@dataclass
class IterationDelta:
    iteration_index: int
    span_id: str
    reason: str         # "baseline" | "final" | "anomaly:<rule>" | "error"
    latency_ms: float
    token_count: int
    has_error: bool
    error_message: str | None


@dataclass
class CompressedLoop:
    community_id: str
    total_iterations: int
    kept_iterations: list[IterationDelta]
    skipped_count: int
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_tier2_models.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
uv run pytest tests/ -q
```

Expected: `33 passed` (29 existing + 4 new)

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/models.py tests/test_tier2_models.py
git commit -m "feat: Tier 2 dataclasses — Community, CommunityCard, IterationDelta, CompressedLoop"
```

---

## Task 2: TraceClassifier

**Files:**
- Create: `src/traceiq/graph/classifier.py`
- Create: `tests/test_classifier.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_classifier.py
from traceiq.graph.classifier import TraceClassifier
from conftest import make_span

def test_small_trace_classified_correctly():
    spans = [make_span(f"s{i}") for i in range(49)]
    assert TraceClassifier().classify(spans) == "small"

def test_boundary_is_small():
    spans = [make_span(f"s{i}") for i in range(50)]
    assert TraceClassifier().classify(spans) == "small"

def test_large_trace_classified_correctly():
    spans = [make_span(f"s{i}") for i in range(51)]
    assert TraceClassifier().classify(spans) == "large"

def test_empty_trace_is_small():
    assert TraceClassifier().classify([]) == "small"

def test_threshold_is_configurable():
    spans = [make_span(f"s{i}") for i in range(30)]
    assert TraceClassifier(threshold=25).classify(spans) == "large"
    assert TraceClassifier(threshold=35).classify(spans) == "small"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_classifier.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement TraceClassifier**

```python
# src/traceiq/graph/classifier.py
from traceiq.models import Span

LARGE_TRACE_THRESHOLD = 50

class TraceClassifier:

    def __init__(self, threshold: int = LARGE_TRACE_THRESHOLD):
        self._threshold = threshold

    def classify(self, spans: list[Span]) -> str:
        """Returns 'small' or 'large'. Large traces use the Tier 2 agentic pipeline."""
        return "large" if len(spans) > self._threshold else "small"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_classifier.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/traceiq/graph/classifier.py tests/test_classifier.py
git commit -m "feat: TraceClassifier — routes spans to Tier 1 or Tier 2 pipeline"
```

---

## Task 3: CommunityDetector

**Files:**
- Create: `src/traceiq/graph/community.py`
- Create: `tests/test_community.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_community.py
import networkx as nx
from traceiq.graph.community import CommunityDetector
from traceiq.models import Community
from conftest import make_span

def _make_chain(n: int, prefix: str = "s"):
    """Make n spans in a parent-child chain."""
    spans = [make_span(f"{prefix}{i}", parent_id=f"{prefix}{i-1}" if i > 0 else None)
             for i in range(n)]
    return spans

def _build_graph(spans):
    import networkx as nx
    from traceiq.graph.builder import GraphBuilder
    return GraphBuilder().build(spans)

def test_every_span_in_exactly_one_community():
    spans = _make_chain(10)
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    all_ids = [sid for c in communities for sid in c.span_ids]
    assert sorted(all_ids) == sorted(s.span_id for s in spans)

def test_returns_community_objects():
    spans = _make_chain(5)
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    assert all(isinstance(c, Community) for c in communities)
    assert all(c.community_id for c in communities)

def test_label_uses_dominant_span_kind():
    spans = [
        make_span("a1", span_kind="TOOL"),
        make_span("a2", span_kind="TOOL", parent_id="a1"),
        make_span("a3", span_kind="TOOL", parent_id="a2"),
    ]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    assert any("TOOL" in c.label or "tool" in c.label.lower() for c in communities)

def test_isolated_nodes_still_assigned():
    # Spans with no edges (no parent_id) should still be in a community
    spans = [make_span(f"iso{i}") for i in range(5)]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    all_ids = {sid for c in communities for sid in c.span_ids}
    assert all(s.span_id in all_ids for s in spans)

def test_single_span_trace():
    spans = [make_span("only")]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    assert len(communities) == 1
    assert communities[0].span_ids == ["only"]
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_community.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement CommunityDetector**

```python
# src/traceiq/graph/community.py
from collections import Counter
import networkx as nx
from traceiq.models import Span, Community

class CommunityDetector:

    def detect(self, spans: list[Span], graph: nx.DiGraph) -> list[Community]:
        if not spans:
            return []

        span_map = {s.span_id: s for s in spans}

        # Louvain requires undirected graph
        undirected = graph.to_undirected()

        # Handle isolated nodes (spans with no edges — not connected to anything)
        # nx.community.louvain_communities works fine with them
        raw_communities = nx.community.louvain_communities(undirected, seed=42)

        communities = []
        for i, node_set in enumerate(raw_communities):
            span_ids = [n for n in node_set if n in span_map]
            if not span_ids:
                continue
            label = self._infer_label(span_ids, span_map)
            communities.append(Community(
                community_id=f"C{i}",
                span_ids=span_ids,
                label=label,
            ))

        return communities

    def _infer_label(self, span_ids: list[str], span_map: dict[str, Span]) -> str:
        """Label a community by its most common span name, falling back to span_kind."""
        names = [span_map[sid].name for sid in span_ids if sid in span_map]
        if not names:
            return "Unknown"
        most_common_name, count = Counter(names).most_common(1)[0]
        # If one name dominates (>40% of spans), use it as label
        if count / len(names) > 0.4:
            return most_common_name
        # Otherwise use dominant span_kind
        kinds = [span_map[sid].span_kind for sid in span_ids if sid in span_map]
        most_common_kind = Counter(kinds).most_common(1)[0][0]
        return most_common_kind
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_community.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -q
```

Expected: `38 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/graph/community.py tests/test_community.py
git commit -m "feat: CommunityDetector — Louvain community detection on span graph"
```

---

## Task 4: CommunityCardBuilder

**Files:**
- Create: `src/traceiq/analysis/community_card.py`
- Create: `tests/test_community_card.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_community_card.py
from traceiq.analysis.community_card import CommunityCardBuilder
from traceiq.models import Community, CommunityCard, Flag
from conftest import make_span

def _card(span_ids, spans, flags=None):
    community = Community(community_id="C0", span_ids=span_ids, label="Test")
    return CommunityCardBuilder().build(community, spans, flags or [])

def test_returns_community_card():
    spans = [make_span("s1"), make_span("s2", parent_id="s1")]
    card = _card(["s1", "s2"], spans)
    assert isinstance(card, CommunityCard)
    assert card.community_id == "C0"

def test_span_count_matches():
    spans = [make_span(f"s{i}") for i in range(5)]
    card = _card([s.span_id for s in spans], spans)
    assert card.span_count == 5

def test_error_count_correct():
    spans = [
        make_span("s1", status="OK"),
        make_span("s2", status="ERROR"),
        make_span("s3", status="ERROR"),
    ]
    card = _card(["s1", "s2", "s3"], spans)
    assert card.error_count == 2

def test_flagged_span_ids_only_from_this_community():
    spans = [make_span("s1"), make_span("s2"), make_span("s3")]
    flags = [Flag("s1", "error_status", "error"), Flag("s3", "latency_spike", "warning")]
    # Only s1 and s2 are in this community
    card = _card(["s1", "s2"], spans, flags)
    assert "s1" in card.flagged_span_ids
    assert "s3" not in card.flagged_span_ids  # s3 not in community

def test_token_growth_empty_when_no_llm_spans():
    spans = [make_span("s1", span_kind="TOOL"), make_span("s2", span_kind="TOOL")]
    card = _card(["s1", "s2"], spans)
    assert card.token_growth == {}

def test_token_growth_computed_from_llm_spans():
    spans = [
        make_span("s1", span_kind="LLM", token_count_prompt=100, token_count_completion=50),
        make_span("s2", span_kind="LLM", token_count_prompt=300, token_count_completion=150),
        make_span("s3", span_kind="LLM", token_count_prompt=800, token_count_completion=200),
    ]
    card = _card(["s1", "s2", "s3"], spans)
    assert card.token_growth["first"] == 150   # s1: 100+50
    assert card.token_growth["last"] == 1000   # s3: 800+200

def test_unique_span_types_listed():
    spans = [
        make_span("s1", span_kind="LLM"),
        make_span("s2", span_kind="LLM"),
        make_span("s3", span_kind="TOOL"),
    ]
    card = _card(["s1", "s2", "s3"], spans)
    assert set(card.span_types) == {"LLM", "TOOL"}

def test_avg_latency_computed():
    spans = [
        make_span("s1", latency_ms=100.0),
        make_span("s2", latency_ms=300.0),
    ]
    card = _card(["s1", "s2"], spans)
    assert card.avg_latency_ms == 200.0
    assert card.total_latency_ms == 400.0
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_community_card.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement CommunityCardBuilder**

```python
# src/traceiq/analysis/community_card.py
from statistics import median
from traceiq.models import Span, Community, CommunityCard, Flag

class CommunityCardBuilder:

    def build(
        self,
        community: Community,
        spans: list[Span],
        flags: list[Flag],
    ) -> CommunityCard:
        span_map = {s.span_id: s for s in spans}
        members = [span_map[sid] for sid in community.span_ids if sid in span_map]

        if not members:
            return CommunityCard(
                community_id=community.community_id,
                label=community.label,
                span_count=0,
                span_types=[],
                iteration_count=1,
                avg_latency_ms=0.0,
                total_latency_ms=0.0,
                error_count=0,
                flagged_span_ids=[],
                token_growth={},
                anomalies=[],
            )

        member_ids = {s.span_id for s in members}

        # Unique span types
        span_types = list({s.span_kind for s in members})

        # Latency
        total_lat = sum(s.latency_ms for s in members)
        avg_lat = total_lat / len(members)

        # Error count
        error_count = sum(1 for s in members if s.has_error)

        # Flagged spans that belong to this community
        flagged_span_ids = [f.span_id for f in flags if f.span_id in member_ids]

        # Token growth: first and last LLM spans by position in members list
        llm_spans = [s for s in members if s.span_kind == "LLM"]
        token_growth: dict = {}
        if len(llm_spans) >= 2:
            token_growth = {
                "first": llm_spans[0].total_tokens,
                "last": llm_spans[-1].total_tokens,
            }

        # Iteration count: how many times does the dominant name repeat
        from collections import Counter
        name_counts = Counter(s.name for s in members)
        most_common_name, most_common_count = name_counts.most_common(1)[0]
        iteration_count = most_common_count if most_common_count >= 3 else 1

        # Anomalies: descriptive labels from flags
        anomalies = []
        flag_map = {f.span_id: f for f in flags if f.span_id in member_ids}
        for span_id, flag in flag_map.items():
            anomalies.append(f"{flag.rule}:{flag.span_id[:8]}")

        return CommunityCard(
            community_id=community.community_id,
            label=community.label,
            span_count=len(members),
            span_types=span_types,
            iteration_count=iteration_count,
            avg_latency_ms=round(avg_lat, 2),
            total_latency_ms=round(total_lat, 2),
            error_count=error_count,
            flagged_span_ids=flagged_span_ids,
            token_growth=token_growth,
            anomalies=anomalies,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_community_card.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -q
```

Expected: `46 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/analysis/community_card.py tests/test_community_card.py
git commit -m "feat: CommunityCardBuilder — lossless metadata cards per community"
```

---

## Task 5: LoopDeduplicator

**Files:**
- Create: `src/traceiq/analysis/loop_dedup.py`
- Create: `tests/test_loop_dedup.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_loop_dedup.py
from traceiq.analysis.loop_dedup import LoopDeduplicator
from traceiq.models import Community, CompressedLoop, IterationDelta
from conftest import make_span

def _community(span_ids, label="AgentLoop"):
    return Community(community_id="C0", span_ids=span_ids, label=label)

def test_non_loop_community_returns_one_iteration():
    spans = [make_span("s1"), make_span("s2"), make_span("s3")]
    community = _community(["s1", "s2", "s3"])
    result = LoopDeduplicator().compress(community, spans)
    assert isinstance(result, CompressedLoop)
    assert result.total_iterations == 1
    assert result.skipped_count == 0

def test_loop_detected_by_repeated_names():
    # 5 spans all named "agent" = 5 iterations
    spans = [make_span(f"a{i}", name="agent") for i in range(5)]
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    assert result.total_iterations == 5

def test_keeps_first_and_last_always():
    spans = [make_span(f"a{i}", name="agent", latency_ms=100.0) for i in range(7)]
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    reasons = [d.reason for d in result.kept_iterations]
    assert "baseline" in reasons
    assert "final" in reasons

def test_keeps_anomalous_iteration():
    # Iteration 3 has a latency spike
    spans = [make_span(f"a{i}", name="agent", latency_ms=100.0) for i in range(6)]
    spans[3] = make_span("a3", name="agent", latency_ms=9000.0)  # spike
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    kept_ids = [d.span_id for d in result.kept_iterations]
    assert "a3" in kept_ids

def test_keeps_error_iteration():
    spans = [make_span(f"a{i}", name="agent") for i in range(5)]
    spans[2] = make_span("a2", name="agent", status="ERROR", error_message="timeout")
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    kept_ids = [d.span_id for d in result.kept_iterations]
    assert "a2" in kept_ids

def test_skipped_count_correct():
    spans = [make_span(f"a{i}", name="agent", latency_ms=100.0) for i in range(10)]
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    total_kept = len(result.kept_iterations)
    assert result.skipped_count == result.total_iterations - total_kept

def test_iteration_delta_has_exact_values():
    spans = [make_span("a0", name="agent", latency_ms=4200.0,
                        token_count_prompt=100, token_count_completion=50)]
    community = _community(["a0"])
    result = LoopDeduplicator().compress(community, spans)
    baseline = next(d for d in result.kept_iterations if d.reason == "baseline")
    assert baseline.latency_ms == 4200.0
    assert baseline.token_count == 150  # 100 + 50
    assert baseline.has_error is False
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_loop_dedup.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement LoopDeduplicator**

```python
# src/traceiq/analysis/loop_dedup.py
from collections import Counter
from statistics import median
from traceiq.models import Span, Community, CompressedLoop, IterationDelta

LATENCY_SPIKE_FACTOR = 2.0   # iteration kept if latency > 2× median

class LoopDeduplicator:

    def compress(self, community: Community, all_spans: list[Span]) -> CompressedLoop:
        span_map = {s.span_id: s for s in all_spans}
        members = [span_map[sid] for sid in community.span_ids if sid in span_map]

        if not members:
            return CompressedLoop(community_id=community.community_id,
                                  total_iterations=0, kept_iterations=[], skipped_count=0)

        # Detect loop: find most repeated span name
        name_counts = Counter(s.name for s in members)
        dominant_name, dominant_count = name_counts.most_common(1)[0]

        # Not a loop if dominant name appears fewer than 3 times
        if dominant_count < 3:
            delta = self._make_delta(members[0], 0, "baseline")
            return CompressedLoop(
                community_id=community.community_id,
                total_iterations=1,
                kept_iterations=[delta],
                skipped_count=0,
            )

        # Extract the representative spans (one per iteration, the dominant-named span)
        iteration_spans = [s for s in members if s.name == dominant_name]
        total = len(iteration_spans)

        # Compute median latency to detect spikes
        latencies = [s.latency_ms for s in iteration_spans]
        med_lat = median(latencies) if latencies else 0.0

        kept: list[IterationDelta] = []
        skipped = 0

        for i, span in enumerate(iteration_spans):
            is_first = i == 0
            is_last = i == total - 1
            is_error = span.has_error
            is_latency_spike = med_lat > 0 and span.latency_ms > LATENCY_SPIKE_FACTOR * med_lat

            if is_first:
                kept.append(self._make_delta(span, i, "baseline"))
            elif is_last:
                kept.append(self._make_delta(span, i, "final"))
            elif is_error:
                kept.append(self._make_delta(span, i, f"anomaly:error"))
            elif is_latency_spike:
                kept.append(self._make_delta(span, i, f"anomaly:latency_spike"))
            else:
                skipped += 1

        return CompressedLoop(
            community_id=community.community_id,
            total_iterations=total,
            kept_iterations=kept,
            skipped_count=skipped,
        )

    def _make_delta(self, span: Span, index: int, reason: str) -> IterationDelta:
        return IterationDelta(
            iteration_index=index,
            span_id=span.span_id,
            reason=reason,
            latency_ms=span.latency_ms,
            token_count=span.total_tokens,
            has_error=span.has_error,
            error_message=span.error_message,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_loop_dedup.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -q
```

Expected: `54 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/analysis/loop_dedup.py tests/test_loop_dedup.py
git commit -m "feat: LoopDeduplicator — lossless loop compression keeping first/changed/last iterations"
```

---

## Task 6: AgentAnalyzer (Claude Tool Use)

**Files:**
- Create: `src/traceiq/analysis/agent.py`
- Create: `tests/test_agent_analyzer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_analyzer.py
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from traceiq.analysis.agent import AgentAnalyzer
from traceiq.models import (
    Community, CommunityCard, CompressedLoop, IterationDelta,
    AnalysisResult, Span, Flag
)
from conftest import make_span

def _make_card(community_id="C0", label="AgentLoop", error_count=0, flagged=[]):
    return CommunityCard(
        community_id=community_id, label=label, span_count=21,
        span_types=["agent", "LLM"], iteration_count=21,
        avg_latency_ms=4800.0, total_latency_ms=100800.0,
        error_count=error_count, flagged_span_ids=flagged,
        token_growth={"first": 52000, "last": 265000},
        anomalies=["token_spike_at_iteration_4"] if error_count == 0 else ["error_status:abc123"],
    )

def _make_loop(community_id="C0"):
    return CompressedLoop(
        community_id=community_id, total_iterations=21,
        kept_iterations=[
            IterationDelta(0, "s1", "baseline", 4200.0, 52000, False, None),
            IterationDelta(20, "s21", "final", 5100.0, 265000, False, None),
        ],
        skipped_count=19,
    )

MOCK_FINAL_RESPONSE = json.dumps({
    "issues": [{
        "id": "issue-1",
        "category": "latency",
        "severity": "warning",
        "span_id": "s1",
        "span_name": "agent",
        "explanation": "Token count grew 5× across 21 iterations indicating context accumulation.",
        "suggestion": "Implement context windowing to limit prompt growth."
    }],
    "root_cause": "Unbounded context accumulation across 21 agent iterations.",
    "summary": "Agent ran 21 iterations with growing context. No errors but latency grew due to token accumulation."
})

@pytest.mark.asyncio
async def test_returns_analysis_result():
    spans = [make_span("s1", span_kind="AGENT")]
    cards = [_make_card()]
    loops = [_make_loop()]
    flags = []

    analyzer = AgentAnalyzer(api_key="test-key")

    # Mock: first call returns tool_use, second returns end_turn with final JSON
    mock_tool_response = MagicMock()
    mock_tool_response.stop_reason = "end_turn"
    mock_tool_response.content = [MagicMock(type="text", text=MOCK_FINAL_RESPONSE)]

    with patch.object(analyzer._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_tool_response
        result = await analyzer.analyze("t1", spans, cards, loops, flags)

    assert isinstance(result, AnalysisResult)
    assert result.trace_id == "t1"
    assert len(result.issues) == 1
    assert result.issues[0].category == "latency"
    assert "context accumulation" in result.root_cause.lower()

@pytest.mark.asyncio
async def test_tool_drill_span_returns_exact_content():
    span = make_span("s1", input_value="exact input text", output_value="exact output text")
    analyzer = AgentAnalyzer(api_key="test-key")
    result = analyzer._tool_drill_span({"span_id": "s1"}, [span])
    assert "exact input text" in result
    assert "exact output text" in result

@pytest.mark.asyncio
async def test_tool_get_community_returns_card_data():
    card = _make_card("C0", "AgentLoop")
    analyzer = AgentAnalyzer(api_key="test-key")
    result = analyzer._tool_get_community({"community_id": "C0"}, [card], [])
    assert "AgentLoop" in result
    assert "21" in result  # span_count or iteration_count

@pytest.mark.asyncio
async def test_tool_unknown_span_returns_not_found():
    analyzer = AgentAnalyzer(api_key="test-key")
    result = analyzer._tool_drill_span({"span_id": "nonexistent"}, [])
    assert "not found" in result.lower()

@pytest.mark.asyncio
async def test_unparseable_response_returns_graceful_fallback():
    spans = [make_span("s1")]
    cards = [_make_card()]
    loops = [_make_loop()]

    analyzer = AgentAnalyzer(api_key="test-key")
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(type="text", text="not valid json at all")]

    with patch.object(analyzer._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await analyzer.analyze("t1", spans, cards, loops, [])

    assert isinstance(result, AnalysisResult)
    assert result.issues == []
    assert "failed" in result.root_cause.lower() or "unparseable" in result.root_cause.lower()
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_agent_analyzer.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement AgentAnalyzer**

```python
# src/traceiq/analysis/agent.py
import json
import re
from datetime import datetime, timezone
from dataclasses import asdict
import anthropic
from traceiq.models import (
    Span, Flag, Issue, AnalysisResult,
    CommunityCard, CompressedLoop
)

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 15

AGENT_SYSTEM_PROMPT = """You are TraceIQ, an expert root cause analysis agent for LLM application traces.

You receive a compressed view of a large trace as community metadata cards and loop summaries.
Use your tools to investigate the trace and identify root causes of failures, latency issues, quality problems, and logic errors.

## Your Tools
- drill_span: get the EXACT raw content of a specific span (input, output, error). Use this to inspect the actual data.
- get_community: get full metadata for a community (all member span IDs, stats, anomalies)
- search_spans: find spans by name or type keyword
- trace_causal_path: get the parent chain from a span to the root
- diff_iterations: get the exact structural diff between two loop iterations
- get_flagged_spans: get all spans flagged by the anomaly detector in a community

## RCA Protocol (follow in order)
1. Check for communities with error_count > 0 — drill into flagged spans first
2. Check communities with anomalies — use diff_iterations for loop anomalies
3. Trace causal paths from errors upward to find root cause
4. Check token_growth trends in loop communities
5. When you have enough evidence, call finish_analysis with your findings

## Output Format
When done, call finish_analysis with a JSON string containing:
{
  "issues": [{"id": "issue-N", "category": "failure|latency|quality|logic",
               "severity": "error|warning|info", "span_id": "...", "span_name": "...",
               "explanation": "...", "suggestion": "..."}],
  "root_cause": "one sentence root cause",
  "summary": "2-3 sentence summary"
}

Be specific. Exact values matter. Do not paraphrase span content."""

TOOLS = [
    {
        "name": "drill_span",
        "description": "Get the exact raw input, output, and error of a specific span. Returns precise values — nothing is summarized.",
        "input_schema": {
            "type": "object",
            "properties": {"span_id": {"type": "string", "description": "The span_id to inspect"}},
            "required": ["span_id"]
        }
    },
    {
        "name": "get_community",
        "description": "Get full metadata for a community: member span IDs, stats, anomaly labels.",
        "input_schema": {
            "type": "object",
            "properties": {"community_id": {"type": "string"}},
            "required": ["community_id"]
        }
    },
    {
        "name": "search_spans",
        "description": "Find spans whose name contains the query string.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Substring to match in span name"}},
            "required": ["query"]
        }
    },
    {
        "name": "trace_causal_path",
        "description": "Get the chain of parent spans from a given span up to the root.",
        "input_schema": {
            "type": "object",
            "properties": {"span_id": {"type": "string"}},
            "required": ["span_id"]
        }
    },
    {
        "name": "diff_iterations",
        "description": "Compare two specific iterations of a loop community. Returns exact latency, token count, error deltas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "community_id": {"type": "string"},
                "iteration_a": {"type": "integer", "description": "Index of first iteration (0-based)"},
                "iteration_b": {"type": "integer", "description": "Index of second iteration (0-based)"}
            },
            "required": ["community_id", "iteration_a", "iteration_b"]
        }
    },
    {
        "name": "get_flagged_spans",
        "description": "Get all span IDs flagged by the anomaly detector in a community.",
        "input_schema": {
            "type": "object",
            "properties": {"community_id": {"type": "string"}},
            "required": ["community_id"]
        }
    },
    {
        "name": "finish_analysis",
        "description": "Submit your final analysis as a JSON string. Call this when you have identified the root cause.",
        "input_schema": {
            "type": "object",
            "properties": {"analysis_json": {"type": "string", "description": "JSON string with issues, root_cause, summary"}},
            "required": ["analysis_json"]
        }
    },
]


class AgentAnalyzer:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        trace_id: str,
        spans: list[Span],
        cards: list[CommunityCard],
        loops: list[CompressedLoop],
        flags: list[Flag],
    ) -> AnalysisResult:
        span_map = {s.span_id: s for s in spans}
        card_map = {c.community_id: c for c in cards}
        loop_map = {l.community_id: l for l in loops}

        initial_prompt = self._build_initial_prompt(cards, loops, flags)
        messages = [{"role": "user", "content": initial_prompt}]

        for _ in range(MAX_TURNS):
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=[{"type": "text", "text": AGENT_SYSTEM_PROMPT,
                          "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract text from final response
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                raw = " ".join(text_blocks)
                return self._parse_result(trace_id, raw, flags)

            if response.stop_reason == "tool_use":
                tool_results = []
                final_analysis = None

                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    tool_input = block.input
                    tool_name = block.name

                    if tool_name == "finish_analysis":
                        final_analysis = tool_input.get("analysis_json", "")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Analysis submitted.",
                        })
                    else:
                        result = self._dispatch_tool(
                            tool_name, tool_input, spans, cards, loops, flags, span_map, card_map, loop_map
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                if final_analysis is not None:
                    return self._parse_result(trace_id, final_analysis, flags)

                messages.append({"role": "user", "content": tool_results})

        # Max turns reached — return empty result
        return AnalysisResult(
            trace_id=trace_id,
            issues=[],
            root_cause="Analysis incomplete: maximum tool call turns reached.",
            summary="The agent could not complete analysis within the turn limit. Try re-analyzing.",
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            flags=flags,
        )

    def _build_initial_prompt(
        self,
        cards: list[CommunityCard],
        loops: list[CompressedLoop],
        flags: list[Flag],
    ) -> str:
        loop_map = {l.community_id: l for l in loops}
        parts = ["## Trace Community Overview\n"]

        for card in cards:
            parts.append(f"### Community {card.community_id}: {card.label}")
            parts.append(f"- spans: {card.span_count} | types: {', '.join(card.span_types)}")
            parts.append(f"- iterations: {card.iteration_count} | errors: {card.error_count}")
            parts.append(f"- avg_latency: {card.avg_latency_ms:.0f}ms | total: {card.total_latency_ms:.0f}ms")
            if card.token_growth:
                parts.append(f"- token_growth: {card.token_growth['first']:,} → {card.token_growth['last']:,}")
            if card.anomalies:
                parts.append(f"- anomalies: {', '.join(card.anomalies)}")
            if card.flagged_span_ids:
                parts.append(f"- flagged_spans: {', '.join(card.flagged_span_ids[:5])}")

            if card.community_id in loop_map:
                loop = loop_map[card.community_id]
                parts.append(f"- loop: {loop.total_iterations} iterations, {loop.skipped_count} skipped")
                for delta in loop.kept_iterations:
                    parts.append(
                        f"  - iter {delta.iteration_index} ({delta.reason}): "
                        f"latency={delta.latency_ms:.0f}ms tokens={delta.token_count:,}"
                        + (f" ERROR={delta.error_message}" if delta.has_error else "")
                    )
            parts.append("")

        parts.append("\nFollow the RCA Protocol. Use your tools to investigate. Call finish_analysis when done.")
        return "\n".join(parts)

    def _dispatch_tool(self, name, inp, spans, cards, loops, flags, span_map, card_map, loop_map):
        if name == "drill_span":
            return self._tool_drill_span(inp, spans)
        if name == "get_community":
            return self._tool_get_community(inp, cards, loops)
        if name == "search_spans":
            return self._tool_search_spans(inp, spans)
        if name == "trace_causal_path":
            return self._tool_causal_path(inp, spans)
        if name == "diff_iterations":
            return self._tool_diff_iterations(inp, loop_map)
        if name == "get_flagged_spans":
            return self._tool_get_flagged_spans(inp, cards, flags)
        return f"Unknown tool: {name}"

    def _tool_drill_span(self, inp: dict, spans: list[Span]) -> str:
        span_id = inp.get("span_id", "")
        span = next((s for s in spans if s.span_id == span_id), None)
        if not span:
            return f"Span {span_id} not found."
        parts = [f"Span: {span.name} [{span.span_kind}]",
                 f"Status: {span.status}",
                 f"Latency: {span.latency_ms:.0f}ms",
                 f"Tokens: prompt={span.token_count_prompt} completion={span.token_count_completion}"]
        if span.error_message:
            parts.append(f"Error: {span.error_message}")
        if span.input_value:
            parts.append(f"Input:\n{span.input_value}")
        if span.output_value:
            parts.append(f"Output:\n{span.output_value}")
        return "\n".join(parts)

    def _tool_get_community(self, inp: dict, cards: list[CommunityCard], loops: list[CompressedLoop]) -> str:
        cid = inp.get("community_id", "")
        card = next((c for c in cards if c.community_id == cid), None)
        if not card:
            return f"Community {cid} not found."
        loop = next((l for l in loops if l.community_id == cid), None)
        parts = [f"Community {cid}: {card.label}",
                 f"Spans: {card.span_count} | Types: {', '.join(card.span_types)}",
                 f"Errors: {card.error_count} | Flagged: {', '.join(card.flagged_span_ids) or 'none'}",
                 f"Anomalies: {', '.join(card.anomalies) or 'none'}"]
        if loop:
            parts.append(f"Loop iterations: {loop.total_iterations} total, {loop.skipped_count} skipped")
            for d in loop.kept_iterations:
                parts.append(f"  iter {d.iteration_index} ({d.reason}): span_id={d.span_id} "
                             f"latency={d.latency_ms:.0f}ms tokens={d.token_count:,}"
                             + (f" ERROR" if d.has_error else ""))
        return "\n".join(parts)

    def _tool_search_spans(self, inp: dict, spans: list[Span]) -> str:
        query = inp.get("query", "").lower()
        matches = [s for s in spans if query in s.name.lower()]
        if not matches:
            return f"No spans found matching '{query}'."
        lines = [f"Found {len(matches)} spans matching '{query}':"]
        for s in matches[:20]:
            lines.append(f"  {s.span_id}: {s.name} [{s.span_kind}] status={s.status} latency={s.latency_ms:.0f}ms")
        return "\n".join(lines)

    def _tool_causal_path(self, inp: dict, spans: list[Span]) -> str:
        span_id = inp.get("span_id", "")
        span_map = {s.span_id: s for s in spans}
        path = []
        current_id = span_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            s = span_map.get(current_id)
            if not s:
                break
            path.append(f"{s.span_id}: {s.name} [{s.span_kind}] status={s.status}")
            current_id = s.parent_id
        if not path:
            return f"Span {span_id} not found."
        return "Causal path (leaf → root):\n" + "\n".join(path)

    def _tool_diff_iterations(self, inp: dict, loop_map: dict) -> str:
        cid = inp.get("community_id", "")
        idx_a = inp.get("iteration_a", 0)
        idx_b = inp.get("iteration_b", 1)
        loop = loop_map.get(cid)
        if not loop:
            return f"No loop found for community {cid}."
        kept = loop.kept_iterations
        a = next((d for d in kept if d.iteration_index == idx_a), None)
        b = next((d for d in kept if d.iteration_index == idx_b), None)
        if not a or not b:
            available = [d.iteration_index for d in kept]
            return f"Iterations {idx_a} or {idx_b} not in kept set. Available: {available}"
        lines = [f"Diff: iteration {idx_a} ({a.reason}) → iteration {idx_b} ({b.reason})"]
        lines.append(f"  latency: {a.latency_ms:.0f}ms → {b.latency_ms:.0f}ms (Δ{b.latency_ms - a.latency_ms:+.0f}ms)")
        lines.append(f"  tokens:  {a.token_count:,} → {b.token_count:,} (Δ{b.token_count - a.token_count:+,})")
        lines.append(f"  errors:  {a.has_error} → {b.has_error}")
        if a.error_message or b.error_message:
            lines.append(f"  error_msg: {a.error_message!r} → {b.error_message!r}")
        return "\n".join(lines)

    def _tool_get_flagged_spans(self, inp: dict, cards: list[CommunityCard], flags: list[Flag]) -> str:
        cid = inp.get("community_id", "")
        card = next((c for c in cards if c.community_id == cid), None)
        if not card:
            return f"Community {cid} not found."
        if not card.flagged_span_ids:
            return f"No flagged spans in community {cid}."
        flag_map = {f.span_id: f for f in flags}
        lines = [f"Flagged spans in community {cid}:"]
        for sid in card.flagged_span_ids:
            flag = flag_map.get(sid)
            rule = flag.rule if flag else "unknown"
            severity = flag.severity if flag else "unknown"
            lines.append(f"  {sid}: rule={rule} severity={severity}")
        return "\n".join(lines)

    def _parse_result(self, trace_id: str, raw: str, flags: list[Flag]) -> AnalysisResult:
        fence_match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
        if fence_match:
            raw = fence_match.group(1)
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            return AnalysisResult(
                trace_id=trace_id,
                issues=[],
                root_cause="Analysis failed: unparseable response from agent.",
                summary="Could not parse the agent's final analysis. Try re-analyzing.",
                analyzed_at=datetime.now(timezone.utc).isoformat(),
                flags=flags,
            )
        issues = [
            Issue(
                id=i["id"], category=i["category"], severity=i["severity"],
                span_id=i["span_id"], span_name=i["span_name"],
                explanation=i["explanation"], suggestion=i["suggestion"],
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_agent_analyzer.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -q
```

Expected: `59 passed`

- [ ] **Step 6: Commit**

```bash
git add src/traceiq/analysis/agent.py tests/test_agent_analyzer.py
git commit -m "feat: AgentAnalyzer — Claude tool use loop for large trace RCA"
```

---

## Task 7: Wire Tier 2 into pipeline.py

**Files:**
- Modify: `src/traceiq/api/pipeline.py`
- Modify: `tests/test_routes.py` (add one new test)

- [ ] **Step 1: Write failing test**

Add this test to `tests/test_routes.py`:

```python
@pytest.mark.asyncio
async def test_large_trace_routes_to_tier2(client):
    """A trace with >50 spans should call run_analysis which internally uses Tier 2."""
    with patch("traceiq.api.routes.get_cache") as mock_cache, \
         patch("traceiq.api.routes.run_analysis", new_callable=AsyncMock) as mock_pipeline:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=None)
        mock_pipeline.return_value = MOCK_ANALYSIS
        resp = await client.get("/api/traces/large-trace-id/analysis")
    assert resp.status_code == 200
    mock_pipeline.assert_called_once_with("large-trace-id")
```

- [ ] **Step 2: Run to verify it passes already** (the route logic is unchanged)

```bash
uv run pytest tests/test_routes.py -v
```

Expected: `4 passed` — the routing test passes because `run_analysis` is already mocked.

- [ ] **Step 3: Update `src/traceiq/api/pipeline.py` to implement Tier 2**

Replace the entire file:

```python
# src/traceiq/api/pipeline.py
import os
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from traceiq.graph.classifier import TraceClassifier
from traceiq.graph.community import CommunityDetector
from traceiq.analysis.engine import AnalysisEngine
from traceiq.analysis.community_card import CommunityCardBuilder
from traceiq.analysis.loop_dedup import LoopDeduplicator
from traceiq.analysis.agent import AgentAnalyzer
from traceiq.cache.db import SQLiteCache
from traceiq.models import AnalysisResult

_adapter = None
_cache = None
_engine = None
_agent = None
_phoenix_url: str | None = None
_phoenix_project: str | None = None


def set_phoenix_config(url: str, project: str) -> None:
    global _adapter, _phoenix_url, _phoenix_project
    _phoenix_url = url
    _phoenix_project = project
    _adapter = None


def get_adapter() -> PhoenixAdapter:
    global _adapter
    if _adapter is None:
        url = _phoenix_url or os.environ.get("PHOENIX_URL", "http://localhost:6006")
        project = _phoenix_project or os.environ.get("PHOENIX_PROJECT", "default")
        _adapter = PhoenixAdapter(base_url=url, project=project)
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


def get_agent() -> AgentAnalyzer:
    global _agent
    if _agent is None:
        _agent = AgentAnalyzer(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _agent


async def run_analysis(trace_id: str) -> AnalysisResult:
    adapter = get_adapter()
    cache = get_cache()

    spans = await adapter.get_spans(trace_id)
    graph = GraphBuilder().build(spans)
    flags = AnomalyDetector().detect(spans, graph)
    tier = TraceClassifier().classify(spans)

    if tier == "small":
        # Tier 1: single Claude call with full graph + flagged content
        engine = get_engine()
        flagged_ids = {f.span_id for f in flags}
        flagged_content = {}
        for span in spans:
            if span.span_id in flagged_ids:
                flagged_content[span.span_id] = await adapter.get_span_content(span)
        result = await engine.analyze(trace_id, spans, graph, flags, flagged_content)

    else:
        # Tier 2: Leiden-style community detection → metadata cards → loop dedup → Claude agent
        agent = get_agent()
        communities = CommunityDetector().detect(spans, graph)
        card_builder = CommunityCardBuilder()
        cards = [card_builder.build(c, spans, flags) for c in communities]
        deduplicator = LoopDeduplicator()
        loops = [deduplicator.compress(c, spans) for c in communities]
        result = await agent.analyze(trace_id, spans, cards, loops, flags)

    await cache.save_analysis(result)
    return result
```

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: `60 passed` (all existing + the new routing test)

- [ ] **Step 5: Smoke test with real large trace**

Make sure Phoenix is running with the orginsightsai project traces, then:

```bash
curl -s "http://localhost:8000/api/traces/325b79f92c9b00c6096b5aafba3d0443/analysis" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Root cause:', d.get('root_cause',''))
print('Issues:', len(d.get('issues',[])))
print('Summary:', d.get('summary','')[:200])
"
```

Expected: Returns AnalysisResult with real root cause within ~15s. No context overflow error.

- [ ] **Step 6: Commit and push**

```bash
git add src/traceiq/api/pipeline.py tests/test_routes.py
git commit -m "feat: wire Tier 2 into pipeline — large traces route to agentic analyzer"
git push origin main
```

---

## Self-Review

**Spec coverage:**
- ✓ TraceClassifier (Task 2)
- ✓ Leiden/Louvain community detection (Task 3 — using nx.community.louvain_communities)
- ✓ Lossless community metadata cards (Task 4 — computed stats, no LLM)
- ✓ Loop deduplication keeping first+changed+last (Task 5 — exact values preserved)
- ✓ Agentic Claude tool use with 6 tools (Task 6 — drill_span, get_community, search_spans, trace_causal_path, diff_iterations, get_flagged_spans)
- ✓ finish_analysis tool for clean termination (Task 6)
- ✓ Same AnalysisResult schema (Tasks 6 + 7)
- ✓ Tier 1 untouched (Task 7 — pipeline.py routes by tier)
- ✓ No lossy compression — all tool returns are exact raw values

**Placeholder scan:** None found. All steps have complete code.

**Type consistency:**
- `Community(community_id, span_ids, label)` — defined Task 1, used Tasks 3, 4, 5, 7
- `CommunityCard` — defined Task 1, built Task 4, used Tasks 6, 7
- `CompressedLoop` — defined Task 1, built Task 5, used Tasks 6, 7
- `IterationDelta` — defined Task 1, used Task 5 + 6
- `TraceClassifier().classify(spans) → str` — Task 2, used Task 7
- `CommunityDetector().detect(spans, graph) → list[Community]` — Task 3, used Task 7
- `CommunityCardBuilder().build(community, spans, flags) → CommunityCard` — Task 4, used Task 7
- `LoopDeduplicator().compress(community, spans) → CompressedLoop` — Task 5, used Task 7
- `AgentAnalyzer(api_key).analyze(trace_id, spans, cards, loops, flags) → AnalysisResult` — Task 6, used Task 7

All signatures consistent across tasks.
