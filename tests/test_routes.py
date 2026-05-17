import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from traceiq.api.app import create_app
from traceiq.models import TraceInfo, Span, AnalysisResult, Issue, Flag

MOCK_TRACES = [
    TraceInfo("t1", "agent-run", "2026-01-01T00:00:00Z", "2026-01-01T00:00:05Z",
              5000.0, 500, 12, False)
]
MOCK_ANALYSIS = AnalysisResult(
    trace_id="t1",
    issues=[Issue("issue-1", "failure", "error", "s1", "agent", "failed", "fix it")],
    root_cause="agent failed",
    summary="one error found",
    analyzed_at="2026-01-01T00:00:10Z",
)

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_list_traces(client):
    with patch("traceiq.api.routes.get_adapter") as mock_adapter, \
         patch("traceiq.api.routes.get_cache") as mock_cache:
        mock_adapter.return_value.list_traces = AsyncMock(return_value=MOCK_TRACES)
        mock_cache.return_value.get_analysis = AsyncMock(return_value=None)
        resp = await client.get("/api/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trace_id"] == "t1"

@pytest.mark.asyncio
async def test_get_analysis_returns_cached(client):
    with patch("traceiq.api.routes.get_cache") as mock_cache:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=MOCK_ANALYSIS)
        resp = await client.get("/api/traces/t1/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "t1"
    assert len(data["issues"]) == 1

@pytest.mark.asyncio
async def test_get_analysis_triggers_pipeline_on_cache_miss(client):
    with patch("traceiq.api.routes.get_cache") as mock_cache, \
         patch("traceiq.api.routes.run_analysis", new_callable=AsyncMock) as mock_pipeline:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=None)
        mock_pipeline.return_value = MOCK_ANALYSIS
        resp = await client.get("/api/traces/t1/analysis")
    assert resp.status_code == 200
    mock_pipeline.assert_called_once_with("t1")

@pytest.mark.asyncio
async def test_large_trace_routes_through_run_analysis(client):
    """run_analysis is always called regardless of trace size — routing happens inside it."""
    with patch("traceiq.api.routes.get_cache") as mock_cache, \
         patch("traceiq.api.routes.run_analysis", new_callable=AsyncMock) as mock_pipeline:
        mock_cache.return_value.get_analysis = AsyncMock(return_value=None)
        mock_pipeline.return_value = MOCK_ANALYSIS
        resp = await client.get("/api/traces/large-trace-id/analysis")
    assert resp.status_code == 200
    mock_pipeline.assert_called_once_with("large-trace-id")
