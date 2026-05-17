import json
import re
from datetime import datetime, timezone
import anthropic
from traceiq.models import (
    Span, Flag, Issue, AnalysisResult,
    CommunityCard, CompressedLoop, IterationDelta
)

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 15

AGENT_SYSTEM_PROMPT = """You are TraceIQ, an expert root cause analysis agent for LLM application traces.

You receive a compressed view of a large trace as community metadata cards and loop summaries.
Use your tools to investigate and identify root causes of failures, latency issues, quality problems, and logic errors.

## RCA Protocol (follow in order)
1. Check communities with error_count > 0 — use get_flagged_spans then drill_span
2. Check communities with anomalies — use diff_iterations for loop anomalies
3. Trace causal paths from errors upward with trace_causal_path
4. Check token_growth trends in loop communities
5. When you have sufficient evidence, call finish_analysis

## finish_analysis JSON format
{
  "issues": [{"id": "issue-N", "category": "failure|latency|quality|logic",
               "severity": "error|warning|info", "span_id": "...", "span_name": "...",
               "explanation": "...", "suggestion": "..."}],
  "root_cause": "one sentence",
  "summary": "2-3 sentences"
}

Be specific. Exact values from spans matter. Do not paraphrase."""

TOOLS = [
    {
        "name": "drill_span",
        "description": "Get exact raw input, output, and error of a specific span. Nothing is summarized.",
        "input_schema": {
            "type": "object",
            "properties": {"span_id": {"type": "string"}},
            "required": ["span_id"]
        }
    },
    {
        "name": "get_community",
        "description": "Get full metadata for a community including member span IDs, stats, loop iterations.",
        "input_schema": {
            "type": "object",
            "properties": {"community_id": {"type": "string"}},
            "required": ["community_id"]
        }
    },
    {
        "name": "search_spans",
        "description": "Find spans whose name contains the query string.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "trace_causal_path",
        "description": "Get the chain of parent spans from a given span up to the root.",
        "input_schema": {
            "type": "object",
            "properties": {"span_id": {"type": "string"}},
            "required": ["span_id"]
        }
    },
    {
        "name": "diff_iterations",
        "description": "Compare two loop iterations by index. Returns exact latency, token, error deltas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "community_id": {"type": "string"},
                "iteration_a": {"type": "integer"},
                "iteration_b": {"type": "integer"}
            },
            "required": ["community_id", "iteration_a", "iteration_b"]
        }
    },
    {
        "name": "get_flagged_spans",
        "description": "Get all span IDs flagged by the anomaly detector in a community.",
        "input_schema": {
            "type": "object",
            "properties": {"community_id": {"type": "string"}},
            "required": ["community_id"]
        }
    },
    {
        "name": "finish_analysis",
        "description": "Submit final analysis JSON. Call when you have identified the root cause.",
        "input_schema": {
            "type": "object",
            "properties": {"analysis_json": {"type": "string"}},
            "required": ["analysis_json"]
        }
    },
]


class AgentAnalyzer:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        trace_id: str,
        spans: list[Span],
        cards: list[CommunityCard],
        loops: list[CompressedLoop],
        flags: list[Flag],
    ) -> AnalysisResult:
        initial_prompt = self._build_initial_prompt(cards, loops)
        messages = [{"role": "user", "content": initial_prompt}]

        for _ in range(MAX_TURNS):
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=[{"type": "text", "text": AGENT_SYSTEM_PROMPT,
                          "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                return self._parse_result(trace_id, " ".join(text_blocks), flags)

            if response.stop_reason == "tool_use":
                tool_results = []
                final_analysis = None

                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if block.name == "finish_analysis":
                        final_analysis = block.input.get("analysis_json", "")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Analysis submitted.",
                        })
                    else:
                        result = self._dispatch_tool(block.name, block.input, spans, cards, loops, flags)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                if final_analysis is not None:
                    return self._parse_result(trace_id, final_analysis, flags)

                messages.append({"role": "user", "content": tool_results})

            # Handle max_tokens — treat as end_turn with whatever text was generated
            if response.stop_reason == "max_tokens":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                raw = " ".join(text_blocks)
                if raw.strip():
                    return self._parse_result(trace_id, raw, flags)
                # No usable text — continue to next turn with a nudge
                messages.append({"role": "user", "content": "Please call finish_analysis with your current findings."})
                continue

        return AnalysisResult(
            trace_id=trace_id, issues=[],
            root_cause="Analysis incomplete: maximum turn limit reached.",
            summary="Agent could not complete analysis within the turn limit. Try re-analyzing.",
            analyzed_at=datetime.now(timezone.utc).isoformat(), flags=flags,
        )

    def _build_initial_prompt(self, cards: list[CommunityCard],
                               loops: list[CompressedLoop]) -> str:
        loop_map = {l.community_id: l for l in loops}
        parts = ["## Trace Community Overview\n"]
        for card in cards:
            parts.append(f"### Community {card.community_id}: {card.label}")
            parts.append(f"- spans: {card.span_count} | types: {', '.join(card.span_types)}")
            parts.append(f"- iterations: {card.iteration_count} | errors: {card.error_count}")
            parts.append(f"- avg_latency: {card.avg_latency_ms:.0f}ms")
            if card.token_growth:
                parts.append(f"- token_growth: {card.token_growth['first']:,} → {card.token_growth['last']:,}")
            if card.anomalies:
                parts.append(f"- anomalies: {', '.join(card.anomalies)}")
            if card.flagged_span_ids:
                parts.append(f"- flagged: {', '.join(card.flagged_span_ids[:5])}")
            if card.community_id in loop_map:
                loop = loop_map[card.community_id]
                parts.append(f"- loop: {loop.total_iterations} iterations, {loop.skipped_count} skipped")
                for d in loop.kept_iterations:
                    err = f" ERROR={d.error_message}" if d.has_error else ""
                    parts.append(f"  - iter {d.iteration_index} ({d.reason}): "
                                 f"latency={d.latency_ms:.0f}ms tokens={d.token_count:,}{err}")
            parts.append("")
        parts.append("Follow the RCA Protocol. Use tools to investigate. Call finish_analysis when done.")
        return "\n".join(parts)

    def _dispatch_tool(self, name: str, inp: dict, spans: list[Span],
                       cards: list[CommunityCard], loops: list[CompressedLoop],
                       flags: list[Flag]) -> str:
        if name == "drill_span":
            return self._tool_drill_span(inp, spans)
        if name == "get_community":
            return self._tool_get_community(inp, cards, loops)
        if name == "search_spans":
            return self._tool_search_spans(inp, spans)
        if name == "trace_causal_path":
            return self._tool_causal_path(inp, spans)
        if name == "diff_iterations":
            return self._tool_diff_iterations(inp, loops)
        if name == "get_flagged_spans":
            return self._tool_get_flagged_spans(inp, cards, flags)
        return f"Unknown tool: {name}"

    def _tool_drill_span(self, inp: dict, spans: list[Span]) -> str:
        span_id = inp.get("span_id", "")
        span = next((s for s in spans if s.span_id == span_id), None)
        if not span:
            return f"Span {span_id} not found."
        parts = [f"Span: {span.name} [{span.span_kind}]",
                 f"Status: {span.status} | Latency: {span.latency_ms:.0f}ms",
                 f"Tokens: prompt={span.token_count_prompt} completion={span.token_count_completion}"]
        if span.error_message:
            parts.append(f"Error: {span.error_message}")
        if span.input_value:
            parts.append(f"Input:\n{span.input_value}")
        if span.output_value:
            parts.append(f"Output:\n{span.output_value}")
        return "\n".join(parts)

    def _tool_get_community(self, inp: dict, cards: list[CommunityCard],
                             loops: list[CompressedLoop]) -> str:
        cid = inp.get("community_id", "")
        card = next((c for c in cards if c.community_id == cid), None)
        if not card:
            return f"Community {cid} not found."
        loop = next((l for l in loops if l.community_id == cid), None)
        parts = [f"Community {cid}: {card.label}",
                 f"Spans: {card.span_count} | Types: {', '.join(card.span_types)}",
                 f"Errors: {card.error_count} | Flagged: {', '.join(card.flagged_span_ids) or 'none'}",
                 f"Anomalies: {', '.join(card.anomalies) or 'none'}"]
        if loop:
            parts.append(f"Loop: {loop.total_iterations} iterations, {loop.skipped_count} skipped")
            for d in loop.kept_iterations:
                err = " ERROR" if d.has_error else ""
                parts.append(f"  iter {d.iteration_index} ({d.reason}): span_id={d.span_id} "
                             f"latency={d.latency_ms:.0f}ms tokens={d.token_count:,}{err}")
        return "\n".join(parts)

    def _tool_search_spans(self, inp: dict, spans: list[Span]) -> str:
        query = inp.get("query", "").lower()
        matches = [s for s in spans if query in s.name.lower()]
        if not matches:
            return f"No spans found matching '{query}'."
        lines = [f"Found {len(matches)} spans matching '{query}':"]
        for s in matches[:20]:
            lines.append(f"  {s.span_id}: {s.name} [{s.span_kind}] status={s.status} "
                        f"latency={s.latency_ms:.0f}ms")
        return "\n".join(lines)

    def _tool_causal_path(self, inp: dict, spans: list[Span]) -> str:
        span_id = inp.get("span_id", "")
        span_map = {s.span_id: s for s in spans}
        path, current_id, visited = [], span_id, set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            s = span_map.get(current_id)
            if not s:
                break
            path.append(f"{s.span_id}: {s.name} [{s.span_kind}] status={s.status}")
            current_id = s.parent_id
        return ("Span not found." if not path else
                "Causal path (leaf → root):\n" + "\n".join(path))

    def _tool_diff_iterations(self, inp: dict, loops: list[CompressedLoop]) -> str:
        cid = inp.get("community_id", "")
        idx_a, idx_b = inp.get("iteration_a", 0), inp.get("iteration_b", 1)
        loop = next((l for l in loops if l.community_id == cid), None)
        if not loop:
            return f"No loop found for community {cid}."
        a = next((d for d in loop.kept_iterations if d.iteration_index == idx_a), None)
        b = next((d for d in loop.kept_iterations if d.iteration_index == idx_b), None)
        if not a or not b:
            available = [d.iteration_index for d in loop.kept_iterations]
            return f"Iterations {idx_a} or {idx_b} not in kept set. Available: {available}"
        return "\n".join([
            f"Diff: iter {idx_a} ({a.reason}) → iter {idx_b} ({b.reason})",
            f"  latency: {a.latency_ms:.0f}ms → {b.latency_ms:.0f}ms (Δ{b.latency_ms-a.latency_ms:+.0f}ms)",
            f"  tokens:  {a.token_count:,} → {b.token_count:,} (Δ{b.token_count-a.token_count:+,})",
            f"  errors:  {a.has_error} → {b.has_error}",
        ])

    def _tool_get_flagged_spans(self, inp: dict, cards: list[CommunityCard],
                                 flags: list[Flag]) -> str:
        cid = inp.get("community_id", "")
        card = next((c for c in cards if c.community_id == cid), None)
        if not card:
            return f"Community {cid} not found."
        if not card.flagged_span_ids:
            return f"No flagged spans in community {cid}."
        flag_map = {f.span_id: f for f in flags}
        lines = [f"Flagged spans in community {cid}:"]
        for sid in card.flagged_span_ids:
            flag = flag_map.get(sid)
            lines.append(f"  {sid}: rule={flag.rule if flag else 'unknown'} "
                        f"severity={flag.severity if flag else 'unknown'}")
        return "\n".join(lines)

    def _parse_result(self, trace_id: str, raw: str, flags: list[Flag]) -> AnalysisResult:
        fence_match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
        if fence_match:
            raw = fence_match.group(1)
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            return AnalysisResult(
                trace_id=trace_id, issues=[],
                root_cause="Analysis failed: unparseable response from agent.",
                summary="Could not parse the agent's final analysis. Try re-analyzing.",
                analyzed_at=datetime.now(timezone.utc).isoformat(), flags=flags,
            )
        issues = [
            Issue(
                id=i.get("id", "issue-unknown"),
                category=i.get("category", "logic"),
                severity=i.get("severity", "info"),
                span_id=i.get("span_id", ""),
                span_name=i.get("span_name", ""),
                explanation=i.get("explanation", ""),
                suggestion=i.get("suggestion", ""),
            )
            for i in data.get("issues", [])
        ]
        return AnalysisResult(
            trace_id=trace_id, issues=issues,
            root_cause=data.get("root_cause", ""),
            summary=data.get("summary", ""),
            analyzed_at=datetime.now(timezone.utc).isoformat(), flags=flags,
        )
