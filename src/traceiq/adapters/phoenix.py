from datetime import datetime, timezone
import httpx
from traceiq.adapters.base import TraceAdapter
from traceiq.models import TraceInfo, Span

class PhoenixAdapter(TraceAdapter):

    def __init__(self, base_url: str, project: str = "default"):
        self._base = base_url.rstrip("/")
        self._project = project
        self._client = httpx.AsyncClient(base_url=self._base, timeout=30.0)

    def _parse_latency(self, start: str, end: str) -> float:
        fmt = "%Y-%m-%dT%H:%M:%S.%f+00:00"
        try:
            s = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc)
            e = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc)
            return (e - s).total_seconds() * 1000
        except Exception:
            return 0.0

    async def list_traces(self, limit: int = 50) -> list[TraceInfo]:
        resp = await self._client.get(f"/v1/projects/{self._project}/traces", params={"limit": limit})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        result = []
        for t in data:
            latency = self._parse_latency(
                t.get("start_time", ""), t.get("end_time", "")
            )
            result.append(TraceInfo(
                trace_id=t["trace_id"],
                name=t.get("name", t["trace_id"][:8]),
                start_time=t.get("start_time", ""),
                end_time=t.get("end_time", ""),
                total_latency_ms=latency,
                token_count_total=t.get("token_count_total", 0) or 0,
                span_count=0,
                has_errors=False,
            ))
        return result

    async def get_spans(self, trace_id: str) -> list[Span]:
        resp = await self._client.get(
            f"/v1/projects/{self._project}/spans",
            params={"limit": 500, "filter": f'trace_id = "{trace_id}"'},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        # Fallback: filter client-side if server filter not supported
        all_ids = [s.get("context", {}).get("trace_id") for s in data]
        if data and all_ids[0] != trace_id:
            data = [s for s in data if s.get("context", {}).get("trace_id") == trace_id]

        spans = []
        for raw in data:
            ctx = raw.get("context", {})
            attrs = raw.get("attributes", {})
            status = raw.get("status", {}).get("status_code", "UNSET")
            start = raw.get("start_time", "")
            end = raw.get("end_time", "")
            latency = self._parse_latency(start, end)
            spans.append(Span(
                span_id=ctx.get("span_id", ""),
                trace_id=ctx.get("trace_id", trace_id),
                parent_id=raw.get("parent_id"),
                name=raw.get("name", "unknown"),
                span_kind=attrs.get("openinference.span.kind", "UNKNOWN"),
                start_time=start,
                end_time=end,
                latency_ms=latency,
                status=status,
                error_message=attrs.get("exception.message") or attrs.get("error.message"),
                input_value=None,   # not loaded yet
                output_value=None,  # not loaded yet
                token_count_prompt=int(attrs.get("llm.token_count.prompt", 0) or 0),
                token_count_completion=int(attrs.get("llm.token_count.completion", 0) or 0),
            ))
        return spans

    async def get_span_content(self, span: Span) -> dict:
        resp = await self._client.get(
            f"/v1/projects/{self._project}/spans",
            params={"limit": 500, "filter": f'trace_id = "{span.trace_id}"'},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        raw = next((s for s in data if s.get("context", {}).get("span_id") == span.span_id), None)
        if not raw:
            return {"input": None, "output": None, "error": None}
        attrs = raw.get("attributes", {})
        return {
            "input": attrs.get("input.value"),
            "output": attrs.get("output.value"),
            "error": attrs.get("exception.message") or attrs.get("error.message"),
        }
