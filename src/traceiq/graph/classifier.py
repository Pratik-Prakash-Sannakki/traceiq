from traceiq.models import Span

LARGE_TRACE_THRESHOLD = 50


class TraceClassifier:

    def __init__(self, threshold: int = LARGE_TRACE_THRESHOLD):
        self._threshold = threshold

    def classify(self, spans: list[Span]) -> str:
        """Returns 'small' or 'large'. Large traces use the Tier 2 agentic pipeline."""
        return "large" if len(spans) > self._threshold else "small"
