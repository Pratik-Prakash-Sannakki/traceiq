from traceiq.models import Community, CommunityCard, IterationDelta, CompressedLoop

def test_community_fields():
    c = Community(community_id="C0", span_ids=["s1", "s2"], label="AgentLoop")
    assert c.community_id == "C0"
    assert "s1" in c.span_ids
    assert c.label == "AgentLoop"

def test_community_card_fields():
    card = CommunityCard(
        community_id="C0", label="AgentLoop", span_count=21,
        span_types=["agent", "call_model"], iteration_count=7,
        avg_latency_ms=4800.0, total_latency_ms=33600.0, error_count=0,
        flagged_span_ids=["s5"], token_growth={"first": 52000, "last": 265000},
        anomalies=["token_spike_at_iteration_4"],
    )
    assert card.span_count == 21
    assert card.token_growth["last"] == 265000

def test_iteration_delta_fields():
    delta = IterationDelta(
        iteration_index=0, span_id="s1", reason="baseline",
        latency_ms=4200.0, token_count=52000, has_error=False, error_message=None,
    )
    assert delta.reason == "baseline"
    assert delta.has_error is False

def test_compressed_loop_fields():
    loop = CompressedLoop(
        community_id="C0", total_iterations=21,
        kept_iterations=[
            IterationDelta(0, "s1", "baseline", 4200.0, 52000, False, None),
            IterationDelta(20, "s21", "final", 5100.0, 265000, False, None),
        ],
        skipped_count=19,
    )
    assert loop.total_iterations == 21
    assert loop.skipped_count == 19
    assert len(loop.kept_iterations) == 2
