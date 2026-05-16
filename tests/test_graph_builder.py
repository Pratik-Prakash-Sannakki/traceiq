import pytest
import networkx as nx
from traceiq.graph.builder import GraphBuilder
from conftest import make_span

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

def test_causal_edge_when_both_parent_and_child_error():
    spans = [
        make_span("s1", status="ERROR", error_message="rate limit"),
        make_span("s2", parent_id="s1", status="ERROR", error_message="upstream failed"),
    ]
    g = GraphBuilder().build(spans)
    assert g.has_edge("s1", "s2")
    assert g["s1"]["s2"]["type"] == "causal"

def test_structural_edge_when_only_child_errors():
    spans = [
        make_span("s1", status="OK"),
        make_span("s2", parent_id="s1", status="ERROR", error_message="boom"),
    ]
    g = GraphBuilder().build(spans)
    assert g.has_edge("s1", "s2")
    assert g["s1"]["s2"]["type"] == "structural"

def test_node_carries_span_metadata():
    spans = [make_span("s1", name="tool", span_kind="TOOL", latency_ms=500.0, status="ERROR")]
    g = GraphBuilder().build(spans)
    node_data = g.nodes["s1"]
    assert node_data["name"] == "tool"
    assert node_data["latency_ms"] == 500.0
    assert node_data["status"] == "ERROR"
    assert node_data["span_kind"] == "TOOL"

def test_root_node_has_no_incoming_edges():
    spans = [
        make_span("s1"),
        make_span("s2", parent_id="s1"),
    ]
    g = GraphBuilder().build(spans)
    roots = [n for n, d in g.in_degree() if d == 0]
    assert roots == ["s1"]

def test_serialize_returns_nodes_and_edges():
    spans = [
        make_span("s1"),
        make_span("s2", parent_id="s1"),
    ]
    g = GraphBuilder().build(spans)
    data = GraphBuilder().serialize(g)
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0]["type"] == "structural"
