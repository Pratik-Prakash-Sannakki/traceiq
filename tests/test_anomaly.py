import pytest
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from conftest import make_span

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
    assert len(loop_flags) == 3
    assert all(f.severity == "error" for f in loop_flags)

def test_flags_missing_output_on_tool():
    spans = [make_span("s1", span_kind="TOOL", output_value=None, status="OK")]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert any(f.span_id == "s1" and f.rule == "missing_output" for f in flags)

def test_does_not_flag_missing_output_on_error_span():
    spans = [make_span("s1", span_kind="TOOL", output_value=None, status="ERROR")]
    g, spans = _build(spans)
    flags = AnomalyDetector().detect(spans, g)
    assert not any(f.rule == "missing_output" for f in flags)
