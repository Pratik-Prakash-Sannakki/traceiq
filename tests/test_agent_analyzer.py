import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from traceiq.analysis.agent import AgentAnalyzer
from traceiq.models import (
    Community, CommunityCard, CompressedLoop, IterationDelta,
    AnalysisResult, Flag
)
from conftest import make_span

def _make_card(community_id="C0", label="AgentLoop", error_count=0, flagged=[]):
    return CommunityCard(
        community_id=community_id, label=label, span_count=21,
        span_types=["agent", "LLM"], iteration_count=21,
        avg_latency_ms=4800.0, total_latency_ms=100800.0,
        error_count=error_count, flagged_span_ids=flagged,
        token_growth={"first": 52000, "last": 265000},
        anomalies=["token_spike_at_iteration_4"],
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
        "id": "issue-1", "category": "latency", "severity": "warning",
        "span_id": "s1", "span_name": "agent",
        "explanation": "Token count grew 5x across 21 iterations.",
        "suggestion": "Implement context windowing."
    }],
    "root_cause": "Unbounded context accumulation across 21 agent iterations.",
    "summary": "Agent ran 21 iterations with growing context. No errors but latency grew."
})

@pytest.mark.asyncio
async def test_returns_analysis_result():
    spans = [make_span("s1", span_kind="AGENT")]
    cards = [_make_card()]
    loops = [_make_loop()]

    analyzer = AgentAnalyzer(api_key="test-key")
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(type="text", text=MOCK_FINAL_RESPONSE)]

    with patch.object(analyzer._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await analyzer.analyze("t1", spans, cards, loops, [])

    assert isinstance(result, AnalysisResult)
    assert result.trace_id == "t1"
    assert len(result.issues) == 1
    assert result.issues[0].category == "latency"
    assert "context" in result.root_cause.lower()

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
    loop = _make_loop("C0")
    analyzer = AgentAnalyzer(api_key="test-key")
    result = analyzer._tool_get_community({"community_id": "C0"}, [card], [loop])
    assert "AgentLoop" in result
    assert "21" in result

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
