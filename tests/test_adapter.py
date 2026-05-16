import pytest
import httpx
from unittest.mock import AsyncMock, patch
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.models import TraceInfo, Span

MOCK_TRACES_RESPONSE = {
    "data": [{
        "trace_id": "abc123",
        "start_time": "2026-01-01T00:00:00.000000+00:00",
        "end_time": "2026-01-01T00:00:05.000000+00:00",
        "token_count_total": 500,
    }]
}

MOCK_SPANS_RESPONSE = {
    "data": [{
        "context": {"span_id": "s1", "trace_id": "abc123"},
        "parent_id": None,
        "name": "agent-run",
        "start_time": "2026-01-01T00:00:00.000000+00:00",
        "end_time": "2026-01-01T00:00:05.000000+00:00",
        "status": {"status_code": "OK"},
        "attributes": {
            "openinference.span.kind": "AGENT",
            "input.value": "What is X?",
            "output.value": "X is Y.",
            "llm.token_count.prompt": 100,
            "llm.token_count.completion": 50,
        },
    }, {
        "context": {"span_id": "s2", "trace_id": "abc123"},
        "parent_id": "s1",
        "name": "llm-call",
        "start_time": "2026-01-01T00:00:01.000000+00:00",
        "end_time": "2026-01-01T00:00:04.000000+00:00",
        "status": {"status_code": "ERROR"},
        "attributes": {
            "openinference.span.kind": "LLM",
            "exception.message": "timeout after 3s",
            "llm.token_count.prompt": 200,
            "llm.token_count.completion": 0,
        },
    }]
}

@pytest.mark.asyncio
async def test_list_traces_returns_trace_info():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_TRACES_RESPONSE, request=httpx.Request("GET", "http://test"))
        traces = await adapter.list_traces(limit=10)
    assert len(traces) == 1
    assert isinstance(traces[0], TraceInfo)
    assert traces[0].trace_id == "abc123"

@pytest.mark.asyncio
async def test_get_spans_normalizes_to_span_dataclass():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_SPANS_RESPONSE, request=httpx.Request("GET", "http://test"))
        spans = await adapter.get_spans("abc123")
    assert len(spans) == 2
    root = next(s for s in spans if s.is_root)
    assert root.name == "agent-run"
    assert root.span_kind == "AGENT"
    assert root.status == "OK"
    err = next(s for s in spans if s.has_error)
    assert err.error_message == "timeout after 3s"
    assert err.token_count_prompt == 200

@pytest.mark.asyncio
async def test_get_span_content_loads_input_output():
    adapter = PhoenixAdapter(base_url="http://localhost:6006", project="default")
    with patch.object(adapter._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=MOCK_SPANS_RESPONSE, request=httpx.Request("GET", "http://test"))
        spans = await adapter.get_spans("abc123")
        content = await adapter.get_span_content(spans[0])
    assert content["input"] == "What is X?"
    assert content["output"] == "X is Y."
