from collections import Counter
from traceiq.models import Span, Community, CommunityCard, Flag


class CommunityCardBuilder:

    def build(self, community: Community, spans: list[Span], flags: list[Flag]) -> CommunityCard:
        span_map = {s.span_id: s for s in spans}
        members = [span_map[sid] for sid in community.span_ids if sid in span_map]

        if not members:
            return CommunityCard(
                community_id=community.community_id, label=community.label,
                span_count=0, span_types=[], iteration_count=1,
                avg_latency_ms=0.0, total_latency_ms=0.0, error_count=0,
                flagged_span_ids=[], token_growth={}, anomalies=[],
            )

        member_ids = {s.span_id for s in members}
        span_types = list({s.span_kind for s in members})
        total_lat = sum(s.latency_ms for s in members)
        avg_lat = total_lat / len(members)
        error_count = sum(1 for s in members if s.has_error)
        flagged_span_ids = [f.span_id for f in flags if f.span_id in member_ids]

        # Token growth: first and last LLM spans in order they appear
        llm_spans = [s for s in members if s.span_kind == "LLM"]
        token_growth: dict[str, int] = {}
        if len(llm_spans) >= 2:
            token_growth = {"first": llm_spans[0].total_tokens, "last": llm_spans[-1].total_tokens}

        # Iteration count: how many times the dominant name appears
        name_counts = Counter(s.name for s in members)
        most_common_count = name_counts.most_common(1)[0][1]
        iteration_count = most_common_count if most_common_count >= 3 else 1

        # Anomalies: one entry per unique flagged span
        seen = set()
        anomalies = []
        for f in flags:
            if f.span_id in member_ids and f.span_id not in seen:
                seen.add(f.span_id)
                anomalies.append(f"{f.rule}:{f.span_id[:8]}")

        return CommunityCard(
            community_id=community.community_id, label=community.label,
            span_count=len(members), span_types=span_types,
            iteration_count=iteration_count,
            avg_latency_ms=round(avg_lat, 2), total_latency_ms=round(total_lat, 2),
            error_count=error_count, flagged_span_ids=flagged_span_ids,
            token_growth=token_growth, anomalies=anomalies,
        )
