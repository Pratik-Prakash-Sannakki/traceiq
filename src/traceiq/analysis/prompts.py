import json
import networkx as nx
from traceiq.models import Span, Flag
from traceiq.graph.builder import GraphBuilder

SYSTEM_PROMPT = """You are TraceIQ, an expert AI system for root cause analysis of LLM application traces.

You receive a directed interaction graph of spans from an AI system (agent or RAG pipeline) and identify root causes of failures, performance problems, quality issues, and logic errors.

You will be given:
1. A graph of spans with metadata (nodes with attributes, edges with types)
2. Pre-flagged suspicious spans (identified by rule-based checks)
3. Full input/output content for those flagged spans only

Return ONLY valid JSON matching this exact schema — no markdown, no explanation outside the JSON:
{
  "issues": [
    {
      "id": "issue-1",
      "category": "failure|latency|quality|logic",
      "severity": "error|warning|info",
      "span_id": "<span_id from the graph>",
      "span_name": "<name of the span>",
      "explanation": "<what went wrong and why — trace causality through graph edges>",
      "suggestion": "<specific, actionable fix — no generic advice>"
    }
  ],
  "root_cause": "<one sentence: the deepest cause in the causal chain>",
  "summary": "<2-3 sentences: overall trace health and main problems>"
}

Rules:
- Trace causality through graph edges. A timeout causing 3 retries is ONE root cause, not 3 issues.
- Distinguish root causes from symptoms (error on child span is symptom; cause is on parent or upstream).
- Be specific in suggestions — name the exact fix, not just "add error handling".
- If no issues found, return empty issues array with a positive summary."""


def build_user_message(
    spans: list[Span],
    graph: nx.DiGraph,
    flags: list[Flag],
    flagged_content: dict[str, dict],
) -> str:
    graph_data = GraphBuilder().serialize(graph)
    flags_data = [{"span_id": f.span_id, "rule": f.rule, "severity": f.severity} for f in flags]

    msg = f"""## Trace Interaction Graph

### Spans (nodes)
{json.dumps(graph_data["nodes"], indent=2)}

### Relationships (edges)
{json.dumps(graph_data["edges"], indent=2)}

### Pre-flagged suspicious spans (rule-based detection)
{json.dumps(flags_data, indent=2)}

## Full content for flagged spans
"""
    if not flagged_content:
        msg += "\n(No suspicious spans — trace appears clean)\n"
    else:
        for span_id, content in flagged_content.items():
            span_name = graph.nodes[span_id].get("name", span_id) if span_id in graph.nodes else span_id
            msg += f"\n### {span_name} (id: {span_id})\n"
            if content.get("input"):
                msg += f"Input:\n{content['input'][:3000]}\n"
            if content.get("output"):
                msg += f"Output:\n{content['output'][:3000]}\n"
            if content.get("error"):
                msg += f"Error: {content['error']}\n"

    msg += "\n\nAnalyze this trace and return the JSON issue report."
    return msg
