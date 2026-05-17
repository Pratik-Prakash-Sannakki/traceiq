from collections import Counter
from statistics import median
from typing import Optional
from traceiq.models import Span, Community, CompressedLoop, IterationDelta

LATENCY_SPIKE_FACTOR = 2.0


class LoopDeduplicator:

    def compress(self, community: Community, all_spans: list[Span]) -> CompressedLoop:
        span_map = {s.span_id: s for s in all_spans}
        members = [span_map[sid] for sid in community.span_ids if sid in span_map]

        if not members:
            return CompressedLoop(community_id=community.community_id,
                                  total_iterations=0, kept_iterations=[], skipped_count=0)

        # Detect loop: most repeated span name
        name_counts = Counter(s.name for s in members)
        dominant_name, dominant_count = name_counts.most_common(1)[0]

        # Not a loop if dominant name appears 3 or fewer times
        if dominant_count <= 3:
            delta = self._make_delta(members[0], 0, "baseline")
            return CompressedLoop(community_id=community.community_id,
                                  total_iterations=1, kept_iterations=[delta], skipped_count=0)

        # Extract iteration spans (dominant-named spans in member order)
        iteration_spans = [s for s in members if s.name == dominant_name]
        total = len(iteration_spans)

        # Median latency to detect spikes
        latencies = [s.latency_ms for s in iteration_spans]
        med_lat = median(latencies) if latencies else 0.0

        kept: list[IterationDelta] = []
        skipped = 0

        for i, span in enumerate(iteration_spans):
            is_first = i == 0
            is_last = i == total - 1
            is_error = span.has_error
            is_spike = med_lat > 0 and span.latency_ms > LATENCY_SPIKE_FACTOR * med_lat

            if is_first:
                kept.append(self._make_delta(span, i, "baseline"))
            elif is_last:
                kept.append(self._make_delta(span, i, "final"))
            elif is_error:
                kept.append(self._make_delta(span, i, "anomaly:error"))
            elif is_spike:
                kept.append(self._make_delta(span, i, "anomaly:latency_spike"))
            else:
                skipped += 1

        return CompressedLoop(community_id=community.community_id,
                              total_iterations=total, kept_iterations=kept, skipped_count=skipped)

    def _make_delta(self, span: Span, index: int, reason: str) -> IterationDelta:
        return IterationDelta(
            iteration_index=index, span_id=span.span_id, reason=reason,
            latency_ms=span.latency_ms, token_count=span.total_tokens,
            has_error=span.has_error, error_message=span.error_message,
        )
