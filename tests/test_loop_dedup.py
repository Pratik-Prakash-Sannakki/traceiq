from traceiq.analysis.loop_dedup import LoopDeduplicator
from traceiq.models import Community, CompressedLoop, IterationDelta
from conftest import make_span


def _community(span_ids, label="AgentLoop"):
    return Community(community_id="C0", span_ids=span_ids, label=label)


def test_non_loop_community_returns_one_iteration():
    spans = [make_span("s1", name="fetch"), make_span("s2", name="parse"), make_span("s3", name="store")]
    community = _community(["s1", "s2", "s3"])
    result = LoopDeduplicator().compress(community, spans)
    assert isinstance(result, CompressedLoop)
    assert result.total_iterations == 1
    assert result.skipped_count == 0


def test_loop_detected_by_repeated_names():
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


def test_empty_community_returns_empty_loop():
    community = _community([])
    result = LoopDeduplicator().compress(community, [])
    assert result.total_iterations == 0
    assert result.kept_iterations == []
    assert result.skipped_count == 0


def test_exactly_3_repetitions_is_a_loop():
    # 3 spans all named "agent" — boundary case: spec says 3+ = loop
    spans = [make_span(f"a{i}", name="agent") for i in range(3)]
    community = _community([s.span_id for s in spans])
    result = LoopDeduplicator().compress(community, spans)
    assert result.total_iterations == 3
    reasons = [d.reason for d in result.kept_iterations]
    assert "baseline" in reasons
    assert "final" in reasons
