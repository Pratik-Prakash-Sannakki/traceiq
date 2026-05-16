from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    span_kind: str          # AGENT, LLM, TOOL, RETRIEVER, EMBEDDING, CHAIN, UNKNOWN
    start_time: str         # ISO 8601
    end_time: str
    latency_ms: float
    status: str             # OK, ERROR, UNSET
    error_message: Optional[str]
    input_value: Optional[str]   # None until explicitly loaded
    output_value: Optional[str]  # None until explicitly loaded
    token_count_prompt: int
    token_count_completion: int

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def has_error(self) -> bool:
        return self.status == "ERROR"

    @property
    def total_tokens(self) -> int:
        return self.token_count_prompt + self.token_count_completion


@dataclass
class TraceInfo:
    trace_id: str
    name: str
    start_time: str
    end_time: str
    total_latency_ms: float
    token_count_total: int
    span_count: int
    has_errors: bool
    issue_count: int = 0        # populated from cache after analysis


@dataclass
class Flag:
    span_id: str
    rule: str       # error_status | latency_spike | loop_detected | token_spike | missing_output | causal_chain
    severity: str   # error | warning | info


@dataclass
class Issue:
    id: str
    category: str   # failure | latency | quality | logic
    severity: str   # error | warning | info
    span_id: str
    span_name: str
    explanation: str
    suggestion: str


@dataclass
class AnalysisResult:
    trace_id: str
    issues: list[Issue]
    root_cause: str
    summary: str
    analyzed_at: str
    flags: list[Flag] = field(default_factory=list)
