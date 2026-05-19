from datetime import datetime
import httpx
from traceiq.adapters.base import TraceAdapter, SpanContent
from traceiq.models import TraceInfo, Span

_KIND_MAP = {
    "llm":       "LLM",
    "chain":     "CHAIN",
    "tool":      "TOOL",
    "retriever": "RETRIEVER",
    "embedding": "EMBEDDING",
    "agent":     "AGENT",
    "prompt":    "UNKNOWN",
    "parser":    "UNKNOWN",
}

_BATCH = 100   # IDs per batch request


class LangSmithAdapter(TraceAdapter):

    def __init__(self, api_key: str, project: str = "default",
                 host: str = "https://api.smith.langchain.com"):
        self._base    = host.rstrip("/")
        self._project = project
        self._headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        self._client  = httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=30.0)
        self._session_id: str | None = None   # cached project UUID

    async def _post(self, path: str, body: dict):
        try:
            r = await self._client.post(path, json=body)
            return r
        except Exception:
            self._client = httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=30.0)
            return await self._client.post(path, json=body)

    async def _get(self, path: str, **params):
        try:
            r = await self._client.get(path, params=params or None)
            return r
        except Exception:
            self._client = httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=30.0)
            return await self._client.get(path, params=params or None)

    def _parse_latency(self, start: str, end: str | None) -> float:
        if not start or not end:
            return 0.0
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return (e - s).total_seconds() * 1000
        except (ValueError, TypeError):
            return 0.0

    async def _get_session_id(self) -> str:
        """Resolve project name → LangSmith session UUID (cached)."""
        if self._session_id:
            return self._session_id
        resp = await self._get("/api/v1/sessions", limit=100)
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"LangSmith authentication failed ({resp.status_code}). "
                "Please generate a fresh API key at smith.langchain.com → Settings → API Keys."
            )
        resp.raise_for_status()
        sessions = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
        for s in sessions:
            if s.get("name", "").lower() == self._project.lower():
                self._session_id = s["id"]
                return self._session_id
        # fall back to first session
        if sessions:
            self._session_id = sessions[0]["id"]
            return self._session_id
        raise RuntimeError(f"LangSmith project '{self._project}' not found.")

    def _run_to_span(self, r: dict, trace_id: str) -> Span:
        latency = self._parse_latency(r.get("start_time", ""), r.get("end_time"))
        status  = "ERROR" if r.get("error") else ("OK" if r.get("end_time") else "UNSET")
        kind    = _KIND_MAP.get((r.get("run_type") or "chain").lower(), "UNKNOWN")
        return Span(
            span_id=r["id"],
            trace_id=trace_id,
            parent_id=r.get("parent_run_id"),
            name=r.get("name", "unknown"),
            span_kind=kind,
            start_time=r.get("start_time", ""),
            end_time=r.get("end_time") or "",
            latency_ms=latency,
            status=status,
            error_message=r.get("error"),
            input_value=None,
            output_value=None,
            token_count_prompt=int(r.get("prompt_tokens") or 0),
            token_count_completion=int(r.get("completion_tokens") or 0),
        )

    async def list_traces(self, limit: int = 50) -> list[TraceInfo]:
        session_id = await self._get_session_id()
        resp = await self._post("/api/v1/runs/query", {
            "session":  [session_id],
            "is_root":  True,
            "limit":    limit,
        })
        resp.raise_for_status()
        runs = resp.json().get("runs", [])

        result = []
        for r in runs:
            trace_id = r.get("trace_id") or r["id"]
            latency  = self._parse_latency(r.get("start_time", ""), r.get("end_time"))
            tokens   = (r.get("total_tokens") or
                        (r.get("prompt_tokens") or 0) + (r.get("completion_tokens") or 0))
            result.append(TraceInfo(
                trace_id=trace_id,
                name=r.get("name") or trace_id[:12],
                start_time=r.get("start_time", ""),
                end_time=r.get("end_time") or "",
                total_latency_ms=latency,
                token_count_total=int(tokens or 0),
                span_count=len(r.get("child_run_ids") or []) + 1,
                has_errors=bool(r.get("error")),
            ))
        return result

    async def get_spans(self, trace_id: str) -> list[Span]:
        # 1. Fetch the root run to get all child IDs
        root_resp = await self._get(f"/api/v1/runs/{trace_id}")
        root_resp.raise_for_status()
        root = root_resp.json()
        child_ids = root.get("child_run_ids") or []

        # 2. Root span itself
        spans: list[Span] = [self._run_to_span(root, trace_id)]

        # 3. Batch-fetch children
        for i in range(0, len(child_ids), _BATCH):
            batch = child_ids[i : i + _BATCH]
            resp  = await self._post("/api/v1/runs/query", {"id": batch})
            if resp.status_code == 200:
                for r in resp.json().get("runs", []):
                    spans.append(self._run_to_span(r, trace_id))

        return spans

    async def get_span_content(self, span: Span) -> SpanContent:
        resp = await self._get(f"/api/v1/runs/{span.span_id}")
        if resp.status_code != 200:
            return {"input": None, "output": None, "error": None}
        r = resp.json()
        return {
            "input":  str(r["inputs"])  if r.get("inputs")  else None,
            "output": str(r["outputs"]) if r.get("outputs") else None,
            "error":  r.get("error"),
        }
