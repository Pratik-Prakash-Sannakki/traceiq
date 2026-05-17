import pytest
from traceiq.cache.db import SQLiteCache
from traceiq.models import Issue, AnalysisResult, Flag


@pytest.fixture
async def cache(tmp_path):
    db_path = str(tmp_path / "test.db")
    c = SQLiteCache(db_path)
    await c.init()
    return c


@pytest.mark.asyncio
async def test_analysis_roundtrip(cache):
    result = AnalysisResult(
        trace_id="t1",
        issues=[Issue("issue-1", "failure", "error", "s1", "tool", "timed out", "add retry")],
        root_cause="tool timeout",
        summary="one error",
        analyzed_at="2026-01-01T00:00:00Z",
        flags=[Flag("s1", "error_status", "error")],
    )
    await cache.save_analysis(result)
    loaded = await cache.get_analysis("t1")
    assert loaded is not None
    assert loaded.trace_id == "t1"
    assert len(loaded.issues) == 1
    assert loaded.issues[0].explanation == "timed out"
    assert loaded.root_cause == "tool timeout"


@pytest.mark.asyncio
async def test_get_analysis_returns_none_for_unknown(cache):
    result = await cache.get_analysis("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_chat_history_roundtrip(cache):
    await cache.save_chat_message("t1", "user", "why did it fail?")
    await cache.save_chat_message("t1", "assistant", "because of a timeout")
    history = await cache.get_chat_history("t1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "because of a timeout"


@pytest.mark.asyncio
async def test_delete_analysis_clears_cache(cache):
    result = AnalysisResult("t1", [], "none", "clean", "2026-01-01T00:00:00Z")
    await cache.save_analysis(result)
    await cache.delete_analysis("t1")
    assert await cache.get_analysis("t1") is None
