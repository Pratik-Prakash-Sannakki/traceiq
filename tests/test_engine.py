import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from traceiq.analysis.engine import AnalysisEngine
from traceiq.models import Flag, Issue, AnalysisResult
from traceiq.graph.builder import GraphBuilder
from conftest import make_span

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
    assert any(
        isinstance(block, dict) and block.get("cache_control") == {"type": "ephemeral"}
        for block in system
    )
