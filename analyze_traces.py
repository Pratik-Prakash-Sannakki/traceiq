"""
Pulls traces from Phoenix and analyzes span count, depth, token volume,
and data size to inform the analysis engine architecture decision.
"""
import json
import requests

PHOENIX = "http://localhost:6006"

def get_spans():
    resp = requests.get(f"{PHOENIX}/v1/spans", params={"limit": 200})
    return resp.json().get("data", [])

def group_by_trace(spans):
    traces = {}
    for s in spans:
        tid = s.get("context", {}).get("trace_id")
        if tid not in traces:
            traces[tid] = []
        traces[tid].append(s)
    return traces

def analyze_trace(trace_id, spans):
    root = next((s for s in spans if not s.get("parent_id")), spans[0])
    name = root.get("name", "unknown")

    # Measure raw JSON size
    raw_json = json.dumps(spans)
    size_kb = len(raw_json.encode()) / 1024

    # Count tokens across all spans
    total_prompt = sum(
        int(s.get("attributes", {}).get("llm.token_count.prompt", 0)) for s in spans
    )
    total_completion = sum(
        int(s.get("attributes", {}).get("llm.token_count.completion", 0)) for s in spans
    )

    # Tree depth
    id_to_span = {s["context"]["span_id"]: s for s in spans}
    def depth(span, d=0):
        children = [s for s in spans if s.get("parent_id") == span["context"]["span_id"]]
        return max([depth(c, d+1) for c in children], default=d)
    max_depth = depth(root)

    # Error spans
    errors = [s for s in spans if s.get("status", {}).get("status_code") == "ERROR"]

    # Span types
    kinds = {}
    for s in spans:
        k = s.get("attributes", {}).get("openinference.span.kind", "UNKNOWN")
        kinds[k] = kinds.get(k, 0) + 1

    print(f"\n{'='*60}")
    print(f"TRACE: {name}")
    print(f"{'='*60}")
    print(f"  Total spans:        {len(spans)}")
    print(f"  Tree depth:         {max_depth} levels")
    print(f"  Error spans:        {len(errors)} ({[e['name'] for e in errors]})")
    print(f"  Span types:         {kinds}")
    print(f"  Total prompt tok:   {total_prompt:,}")
    print(f"  Total output tok:   {total_completion:,}")
    print(f"  Raw JSON size:      {size_kb:.1f} KB")
    print(f"\n  >> Feasibility note:")
    if size_kb < 50:
        print(f"     {size_kb:.1f} KB fits easily in Claude context. In-memory graph viable.")
    elif size_kb < 200:
        print(f"     {size_kb:.1f} KB is manageable but inputs/outputs need trimming.")
    else:
        print(f"     {size_kb:.1f} KB is too large for context. KG compression required.")

    print(f"\n  Span tree:")
    def print_tree(span, indent=0):
        kind = span.get("attributes", {}).get("openinference.span.kind", "")
        err = " ❌ ERROR" if span.get("status", {}).get("status_code") == "ERROR" else ""
        print(f"  {'  ' * indent}└─ {span['name']} [{kind}]{err}")
        children = [s for s in spans if s.get("parent_id") == span["context"]["span_id"]]
        for c in children:
            print_tree(c, indent + 1)
    print_tree(root)

    return {
        "name": name,
        "span_count": len(spans),
        "depth": max_depth,
        "errors": len(errors),
        "size_kb": size_kb,
        "total_tokens": total_prompt + total_completion,
    }

if __name__ == "__main__":
    print("Fetching traces from Phoenix...")
    spans = get_spans()
    print(f"Total spans fetched: {len(spans)}")

    traces = group_by_trace(spans)
    print(f"Total traces: {len(traces)}")

    results = []
    for tid, tspans in traces.items():
        r = analyze_trace(tid, tspans)
        results.append(r)

    print(f"\n{'='*60}")
    print("FEASIBILITY SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"\n  {r['name']}")
        print(f"    Spans: {r['span_count']} | Depth: {r['depth']} | "
              f"Errors: {r['errors']} | Size: {r['size_kb']:.1f}KB | "
              f"Tokens: {r['total_tokens']:,}")

    avg_size = sum(r['size_kb'] for r in results) / len(results) if results else 0
    print(f"\n  Avg raw trace size: {avg_size:.1f} KB")
    print(f"  At 100 traces/day:  {avg_size * 100 / 1024:.1f} MB/day of raw trace data")
    print(f"  Claude context:     200K tokens ≈ ~800 KB")
    print(f"\n  Verdict:")
    if avg_size < 100:
        print("  ✓ Single trace fits in context — in-memory graph per trace is viable.")
        print("  ✓ But at scale (1000s of traces), cross-trace analysis needs KG/embeddings.")
    else:
        print("  ✗ Traces too large for naive context dump — KG compression is required.")
