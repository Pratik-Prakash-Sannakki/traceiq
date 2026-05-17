import pytest
from traceiq.models import Span
import traceiq.api.pipeline as pipeline_module

@pytest.fixture(autouse=True)
def reset_pipeline_singletons():
    """Reset pipeline singletons before and after each test to prevent leakage."""
    pipeline_module._adapter = None
    pipeline_module._cache = None
    pipeline_module._engine = None
    yield
    pipeline_module._adapter = None
    pipeline_module._cache = None
    pipeline_module._engine = None

def make_span(
    span_id: str = "s1",
    trace_id: str = "t1",
    parent_id: str | None = None,
    name: str = "test-span",
    span_kind: str = "TOOL",
    latency_ms: float = 100.0,
    status: str = "OK",
    error_message: str | None = None,
    input_value: str | None = None,
    output_value: str | None = None,
    token_count_prompt: int = 0,
    token_count_completion: int = 0,
) -> Span:
    return Span(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=name,
        span_kind=span_kind,
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:01Z",
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
        input_value=input_value,
        output_value=output_value,
        token_count_prompt=token_count_prompt,
        token_count_completion=token_count_completion,
    )

@pytest.fixture
def span_factory():
    return make_span
