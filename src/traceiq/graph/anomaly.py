from collections import defaultdict
from statistics import median
import networkx as nx
from traceiq.models import Span, Flag

class AnomalyDetector:

    def detect(self, spans: list[Span], graph: nx.DiGraph) -> list[Flag]:
        flags: list[Flag] = []
        flags.extend(self._error_status(spans))
        flags.extend(self._latency_spike(spans))
        flags.extend(self._loop_detected(spans))
        flags.extend(self._token_spike(spans))
        flags.extend(self._missing_output(spans))
        return flags

    def _error_status(self, spans: list[Span]) -> list[Flag]:
        return [
            Flag(s.span_id, "error_status", "error")
            for s in spans if s.has_error
        ]

    def _latency_spike(self, spans: list[Span]) -> list[Flag]:
        by_kind: dict[str, list[Span]] = defaultdict(list)
        for s in spans:
            by_kind[s.span_kind].append(s)

        flags = []
        for kind, group in by_kind.items():
            if len(group) < 2:
                continue
            med = median(s.latency_ms for s in group)
            if med == 0:
                continue
            for s in group:
                if s.latency_ms > 2 * med:
                    flags.append(Flag(s.span_id, "latency_spike", "warning"))
        return flags

    def _loop_detected(self, spans: list[Span]) -> list[Flag]:
        name_to_ids: dict[str, list[str]] = defaultdict(list)
        for s in spans:
            name_to_ids[s.name].append(s.span_id)

        flags = []
        for name, ids in name_to_ids.items():
            if len(ids) >= 3:
                for sid in ids:
                    flags.append(Flag(sid, "loop_detected", "error"))
        return flags

    def _token_spike(self, spans: list[Span]) -> list[Flag]:
        llm_spans = [s for s in spans if s.span_kind == "LLM"]
        if len(llm_spans) < 2:
            return []
        med = median(s.total_tokens for s in llm_spans)
        if med == 0:
            return []
        return [
            Flag(s.span_id, "token_spike", "warning")
            for s in llm_spans if s.total_tokens > 2 * med
        ]

    def _missing_output(self, spans: list[Span]) -> list[Flag]:
        return [
            Flag(s.span_id, "missing_output", "warning")
            for s in spans
            if s.span_kind == "TOOL" and s.output_value is None and not s.has_error
        ]
