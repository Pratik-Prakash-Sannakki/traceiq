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
