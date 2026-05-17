import os
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from traceiq.analysis.engine import AnalysisEngine
from traceiq.cache.db import SQLiteCache
from traceiq.models import AnalysisResult

_adapter = None
_cache = None
_engine = None
_phoenix_url: str | None = None
_phoenix_project: str | None = None


def set_phoenix_config(url: str, project: str) -> None:
    global _adapter, _phoenix_url, _phoenix_project
    _phoenix_url = url
    _phoenix_project = project
    _adapter = None  # force re-create on next call


def get_adapter() -> PhoenixAdapter:
    global _adapter
    if _adapter is None:
        url = _phoenix_url or os.environ.get("PHOENIX_URL", "http://localhost:6006")
        project = _phoenix_project or os.environ.get("PHOENIX_PROJECT", "default")
        _adapter = PhoenixAdapter(base_url=url, project=project)
    return _adapter

def get_cache() -> SQLiteCache:
    global _cache
    if _cache is None:
        _cache = SQLiteCache(os.environ.get("TRACEIQ_DB_PATH", "traceiq.db"))
    return _cache

def get_engine() -> AnalysisEngine:
    global _engine
    if _engine is None:
        _engine = AnalysisEngine(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _engine

async def run_analysis(trace_id: str) -> AnalysisResult:
    adapter = get_adapter()
    cache = get_cache()
    engine = get_engine()

    spans = await adapter.get_spans(trace_id)
    graph = GraphBuilder().build(spans)
    flags = AnomalyDetector().detect(spans, graph)

    flagged_ids = {f.span_id for f in flags}
    flagged_content = {}
    for span in spans:
        if span.span_id in flagged_ids:
            flagged_content[span.span_id] = await adapter.get_span_content(span)

    result = await engine.analyze(trace_id, spans, graph, flags, flagged_content)
    await cache.save_analysis(result)
    return result
