import os
from dataclasses import asdict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from traceiq.api.pipeline import get_adapter, get_cache, get_engine, run_analysis

router = APIRouter(prefix="/api")

@router.get("/traces")
async def list_traces(limit: int = 50):
    adapter = get_adapter()
    traces = await adapter.list_traces(limit=limit)
    cache = get_cache()
    result = []
    for t in traces:
        analysis = await cache.get_analysis(t.trace_id)
        t.issue_count = len(analysis.issues) if analysis else 0
        result.append(asdict(t))
    return result

@router.get("/traces/{trace_id}/analysis")
async def get_analysis(trace_id: str, reanalyze: bool = False):
    cache = get_cache()
    if not reanalyze:
        cached = await cache.get_analysis(trace_id)
        if cached:
            return {
                "trace_id": cached.trace_id,
                "issues": [asdict(i) for i in cached.issues],
                "root_cause": cached.root_cause,
                "summary": cached.summary,
                "analyzed_at": cached.analyzed_at,
            }
    result = await run_analysis(trace_id)
    return {
        "trace_id": result.trace_id,
        "issues": [asdict(i) for i in result.issues],
        "root_cause": result.root_cause,
        "summary": result.summary,
        "analyzed_at": result.analyzed_at,
    }

class ChatRequest(BaseModel):
    message: str

@router.post("/traces/{trace_id}/chat")
async def chat(trace_id: str, req: ChatRequest):
    cache = get_cache()
    engine = get_engine()
    adapter = get_adapter()

    analysis = await cache.get_analysis(trace_id)
    if not analysis:
        analysis = await run_analysis(trace_id)

    spans = await adapter.get_spans(trace_id)
    from traceiq.graph.builder import GraphBuilder
    graph = GraphBuilder().build(spans)
    history = await cache.get_chat_history(trace_id)

    await cache.save_chat_message(trace_id, "user", req.message)

    async def stream():
        full = ""
        async for chunk in engine.chat(trace_id, spans, graph, analysis, history, req.message):
            full += chunk
            yield chunk
        await cache.save_chat_message(trace_id, "assistant", full)

    return StreamingResponse(stream(), media_type="text/plain")


@router.get("/settings")
async def get_settings():
    cache = get_cache()
    return {
        "phoenix_url": await cache.get_setting("phoenix_url", os.environ.get("PHOENIX_URL", "http://localhost:6006")),
        "phoenix_project": await cache.get_setting("phoenix_project", os.environ.get("PHOENIX_PROJECT", "default")),
    }


class SettingsRequest(BaseModel):
    phoenix_url: str
    phoenix_project: str


@router.post("/settings")
async def save_settings(req: SettingsRequest):
    from traceiq.api.pipeline import set_phoenix_config
    cache = get_cache()
    await cache.save_setting("phoenix_url", req.phoenix_url.rstrip("/"))
    await cache.save_setting("phoenix_project", req.phoenix_project)
    set_phoenix_config(req.phoenix_url.rstrip("/"), req.phoenix_project)
    return {"status": "saved"}
