import json
from datetime import datetime, timezone
import anthropic
import networkx as nx
from traceiq.models import Span, Flag, Issue, AnalysisResult
from traceiq.analysis.prompts import SYSTEM_PROMPT, build_user_message

MODEL = "claude-sonnet-4-6"

class AnalysisEngine:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        trace_id: str,
        spans: list[Span],
        graph: nx.DiGraph,
        flags: list[Flag],
        flagged_content: dict[str, dict],
    ) -> AnalysisResult:
        user_msg = build_user_message(spans, graph, flags, flagged_content)

        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        issues = [
            Issue(
                id=i["id"],
                category=i["category"],
                severity=i["severity"],
                span_id=i["span_id"],
                span_name=i["span_name"],
                explanation=i["explanation"],
                suggestion=i["suggestion"],
            )
            for i in data.get("issues", [])
        ]

        return AnalysisResult(
            trace_id=trace_id,
            issues=issues,
            root_cause=data.get("root_cause", ""),
            summary=data.get("summary", ""),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            flags=flags,
        )

    async def chat(
        self,
        trace_id: str,
        spans: list[Span],
        graph: nx.DiGraph,
        analysis: AnalysisResult,
        history: list[dict],
        user_message: str,
    ):
        """Stream a chat response. Yields text chunks."""
        context = build_user_message(spans, graph, analysis.flags, {})
        system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {
                "type": "text",
                "text": f"## Previous analysis\n{json.dumps({'issues': [{'id': i.id, 'category': i.category, 'severity': i.severity, 'span_id': i.span_id, 'span_name': i.span_name, 'explanation': i.explanation, 'suggestion': i.suggestion} for i in analysis.issues], 'root_cause': analysis.root_cause, 'summary': analysis.summary}, indent=2)}",
                "cache_control": {"type": "ephemeral"},
            },
            {"type": "text", "text": f"## Trace graph context\n{context}"},
        ]
        messages = history + [{"role": "user", "content": user_message}]

        async with self._client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
