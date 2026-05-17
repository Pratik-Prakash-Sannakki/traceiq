# src/traceiq/api/pipeline.py
import os
from traceiq.adapters.phoenix import PhoenixAdapter
from traceiq.graph.builder import GraphBuilder
from traceiq.graph.anomaly import AnomalyDetector
from traceiq.graph.classifier import TraceClassifier
from traceiq.graph.community import CommunityDetector
from traceiq.analysis.engine import AnalysisEngine
from traceiq.analysis.community_card import CommunityCardBuilder
from traceiq.analysis.loop_dedup import LoopDeduplicator
from traceiq.analysis.agent import AgentAnalyzer
from traceiq.cache.db import SQLiteCache
from traceiq.models import AnalysisResult

_adapter = None
_cache = None
_engine = None
_agent = None
_phoenix_url: str | None = None
_phoenix_project: str | None = None


def set_phoenix_config(url: str, project: str) -> None:
    global _adapter, _phoenix_url, _phoenix_project
    _phoenix_url = url
    _phoenix_project = project
    _adapter = None


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


def get_agent() -> AgentAnalyzer:
    global _agent
    if _agent is None:
        _agent = AgentAnalyzer(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _agent


async def run_analysis(trace_id: str) -> AnalysisResult:
    adapter = get_adapter()
    cache = get_cache()

    spans = await adapter.get_spans(trace_id)
    graph = GraphBuilder().build(spans)
    flags = AnomalyDetector().detect(spans, graph)
    tier = TraceClassifier().classify(spans)

    if tier == "small":
        # Tier 1: single Claude call with graph + flagged span content
        engine = get_engine()
        flagged_ids = {f.span_id for f in flags}
        flagged_content = {}
        for span in spans:
            if span.span_id in flagged_ids:
                flagged_content[span.span_id] = await adapter.get_span_content(span)
        result = await engine.analyze(trace_id, spans, graph, flags, flagged_content)
    else:
        # Tier 2: community detection → metadata cards → loop dedup → Claude agent
        agent = get_agent()
        communities = CommunityDetector().detect(spans, graph)
        card_builder = CommunityCardBuilder()
        cards = [card_builder.build(c, spans, flags) for c in communities]
        loops = [LoopDeduplicator().compress(c, spans) for c in communities]
        result = await agent.analyze(trace_id, spans, cards, loops, flags)

    await cache.save_analysis(result)
    return result
