from abc import ABC, abstractmethod
from traceiq.models import TraceInfo, Span

class TraceAdapter(ABC):

    @abstractmethod
    async def list_traces(self, limit: int = 50) -> list[TraceInfo]:
        """Return recent traces sorted by start_time desc."""

    @abstractmethod
    async def get_spans(self, trace_id: str) -> list[Span]:
        """Return all spans for a trace, with input/output as None (metadata only)."""

    @abstractmethod
    async def get_span_content(self, span: Span) -> dict:
        """Return {"input": str|None, "output": str|None, "error": str|None} for a span."""
