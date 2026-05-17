from collections import Counter
import networkx as nx
from traceiq.models import Span, Community


class CommunityDetector:

    def detect(self, spans: list[Span], graph: nx.DiGraph) -> list[Community]:
        if not spans:
            return []

        span_map = {s.span_id: s for s in spans}

        # Louvain requires undirected graph
        undirected = graph.to_undirected()

        # nx.community.louvain_communities returns list of sets of node IDs
        raw_communities = nx.community.louvain_communities(undirected, seed=42)

        communities = []
        for i, node_set in enumerate(raw_communities):
            span_ids = [n for n in node_set if n in span_map]
            if not span_ids:
                continue
            label = self._infer_label(span_ids, span_map)
            communities.append(Community(
                community_id=f"C{i}",
                span_ids=span_ids,
                label=label,
            ))

        return communities

    def _infer_label(self, span_ids: list[str], span_map: dict[str, Span]) -> str:
        names = [span_map[sid].name for sid in span_ids if sid in span_map]
        if not names:
            return "Unknown"
        most_common_name, count = Counter(names).most_common(1)[0]
        if count / len(names) > 0.4:
            return most_common_name
        kinds = [span_map[sid].span_kind for sid in span_ids if sid in span_map]
        return Counter(kinds).most_common(1)[0][0]
