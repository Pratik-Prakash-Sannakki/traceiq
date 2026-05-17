from traceiq.graph.classifier import TraceClassifier
from conftest import make_span


def test_small_trace_classified_correctly():
    spans = [make_span(f"s{i}") for i in range(49)]
    assert TraceClassifier().classify(spans) == "small"


def test_boundary_is_small():
    spans = [make_span(f"s{i}") for i in range(50)]
    assert TraceClassifier().classify(spans) == "small"


def test_large_trace_classified_correctly():
    spans = [make_span(f"s{i}") for i in range(51)]
    assert TraceClassifier().classify(spans) == "large"


def test_empty_trace_is_small():
    assert TraceClassifier().classify([]) == "small"


def test_threshold_is_configurable():
    spans = [make_span(f"s{i}") for i in range(30)]
    assert TraceClassifier(threshold=25).classify(spans) == "large"
    assert TraceClassifier(threshold=35).classify(spans) == "small"
