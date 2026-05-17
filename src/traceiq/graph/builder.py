import math
import networkx as nx
from traceiq.models import Span

def _safe(v):
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v

class GraphBuilder:

    def build(self, spans: list[Span]) -> nx.DiGraph:
        G = nx.DiGraph()

        for s in spans:
            G.add_node(s.span_id,
                span_id=s.span_id,
                name=s.name,
                span_kind=s.span_kind,
                latency_ms=s.latency_ms,
                status=s.status,
                error_message=s.error_message,
                token_count_prompt=s.token_count_prompt,
                token_count_completion=s.token_count_completion,
                start_time=s.start_time,
                end_time=s.end_time,
            )

        for s in spans:
            if s.parent_id and s.parent_id in G:
                G.add_edge(s.parent_id, s.span_id, type="structural")

        error_ids = {s.span_id for s in spans if s.has_error}
        for s in spans:
            if s.has_error and s.parent_id in error_ids:
                if G.has_edge(s.parent_id, s.span_id):
                    G[s.parent_id][s.span_id]["type"] = "causal"

        return G

    def serialize(self, G: nx.DiGraph) -> dict:
        return {
            "nodes": [
                {k: _safe(v) for k, v in data.items()}
                for _, data in G.nodes(data=True)
            ],
            "edges": [
                {"from": u, "to": v, "type": d.get("type")}
                for u, v, d in G.edges(data=True)
            ],
        }
