import networkx as nx
from traceiq.graph.community import CommunityDetector
from traceiq.graph.builder import GraphBuilder
from traceiq.models import Community
from conftest import make_span


def _build_graph(spans):
    return GraphBuilder().build(spans)


def test_every_span_in_exactly_one_community():
    spans = [make_span(f"s{i}", parent_id=f"s{i-1}" if i > 0 else None) for i in range(10)]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    all_ids = [sid for c in communities for sid in c.span_ids]
    assert sorted(all_ids) == sorted(s.span_id for s in spans)


def test_returns_community_objects():
    spans = [make_span(f"s{i}", parent_id=f"s{i-1}" if i > 0 else None) for i in range(5)]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    assert all(isinstance(c, Community) for c in communities)
    assert all(c.community_id for c in communities)


def test_label_uses_dominant_span_name():
    # All 3 spans have name "test-span" (>40% threshold) — label should be "test-span"
    spans = [
        make_span("a1", name="test-span", span_kind="TOOL"),
        make_span("a2", name="test-span", span_kind="TOOL", parent_id="a1"),
        make_span("a3", name="test-span", span_kind="TOOL", parent_id="a2"),
    ]
    graph = _build_graph(spans)
    communities = CommunityDetector().detect(spans, graph)
    # All spans connected in a chain — one community; dominant name = "test-span"
    assert len(communities) == 1
    assert communities[0].label == "test-span"


def test_isolated_nodes_still_assigned():
    spans = [make_span(f"iso{i}") for i in range(5)]  # no parents = no edges
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
