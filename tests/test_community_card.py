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
    spans = [make_span("s1", latency_ms=100.0), make_span("s2", latency_ms=300.0)]
    card = _card(["s1", "s2"], spans)
    assert card.avg_latency_ms == 200.0
    assert card.total_latency_ms == 400.0

def test_iteration_count_one_when_no_dominant_name():
    # 3 different span names — no name appears 3+ times
    spans = [
        make_span("s1", name="retrieve"),
        make_span("s2", name="generate"),
        make_span("s3", name="validate"),
    ]
    card = _card(["s1", "s2", "s3"], spans)
    assert card.iteration_count == 1

def test_iteration_count_matches_dominant_repetitions():
    # "agent" appears 4 times → loop of 4 iterations
    spans = [make_span(f"a{i}", name="agent") for i in range(4)]
    card = _card([s.span_id for s in spans], spans)
    assert card.iteration_count == 4

def test_anomalies_format():
    spans = [make_span("s1"), make_span("s2")]
    flags = [Flag("s1", "error_status", "error")]
    card = _card(["s1", "s2"], spans, flags)
    assert len(card.anomalies) == 1
    assert card.anomalies[0] == f"error_status:{flags[0].span_id[:8]}"

def test_anomalies_deduped_per_span():
    # Same span flagged twice — only one anomaly entry
    spans = [make_span("s1")]
    flags = [Flag("s1", "error_status", "error"), Flag("s1", "latency_spike", "warning")]
    card = _card(["s1"], spans, flags)
    assert len(card.anomalies) == 1
