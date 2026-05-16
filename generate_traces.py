"""
Generates realistic synthetic traces for feasibility analysis.
Simulates: (1) complex RAG pipeline, (2) multi-step agent with tool calls and a loop.
"""
import time
import random
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues

PHOENIX_ENDPOINT = "http://localhost:6006/v1/traces"

provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("traceiq.synthetic")

def ms(n): return n / 1000.0

def rand_chunk():
    topics = ["neural networks", "transformer architecture", "attention mechanism",
               "gradient descent", "backpropagation", "reinforcement learning",
               "knowledge graphs", "vector embeddings", "RAG systems", "LLM fine-tuning"]
    return f"...{random.choice(topics)} is a fundamental concept in modern AI research. " * 3

# ─────────────────────────────────────────────
# TRACE 1: Complex RAG pipeline (realistic scale)
# ─────────────────────────────────────────────
def generate_rag_trace():
    query = "Explain the difference between RAG and fine-tuning for domain adaptation"
    print(f"\n[RAG TRACE] Generating: '{query}'")

    with tracer.start_as_current_span("rag-pipeline") as root:
        root.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.CHAIN.value)
        root.set_attribute(SpanAttributes.INPUT_VALUE, query)
        time.sleep(ms(50))

        # Query rewriting — 3 sub-queries
        with tracer.start_as_current_span("query-rewriter") as qr:
            qr.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            qr.set_attribute(SpanAttributes.INPUT_VALUE, query)
            qr.set_attribute(SpanAttributes.LLM_MODEL_NAME, "gpt-4o")
            qr.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 245)
            qr.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 89)
            time.sleep(ms(820))
            sub_queries = [
                "What is RAG and how does it work?",
                "What is fine-tuning in LLMs?",
                "When to use RAG vs fine-tuning for domain-specific tasks?"
            ]
            qr.set_attribute(SpanAttributes.OUTPUT_VALUE, str(sub_queries))

        # Parallel retrieval for each sub-query (sequential here for simplicity)
        all_chunks = []
        for i, sq in enumerate(sub_queries):
            with tracer.start_as_current_span(f"retriever-{i+1}") as ret:
                ret.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.RETRIEVER.value)
                ret.set_attribute(SpanAttributes.INPUT_VALUE, sq)
                time.sleep(ms(random.randint(180, 450)))

                # Embedding call
                with tracer.start_as_current_span(f"embed-query-{i+1}") as emb:
                    emb.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.EMBEDDING.value)
                    emb.set_attribute(SpanAttributes.EMBEDDING_MODEL_NAME, "text-embedding-3-small")
                    emb.set_attribute(SpanAttributes.INPUT_VALUE, sq)
                    time.sleep(ms(random.randint(60, 120)))
                    emb.set_attribute(SpanAttributes.OUTPUT_VALUE, "[0.021, -0.034, 0.091, ...]")

                # Vector DB lookup
                with tracer.start_as_current_span(f"vector-db-search-{i+1}") as vdb:
                    vdb.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.TOOL.value)
                    vdb.set_attribute("db.system", "pinecone")
                    vdb.set_attribute(SpanAttributes.INPUT_VALUE, f"top_k=8, namespace=docs, query={sq[:40]}")
                    time.sleep(ms(random.randint(90, 200)))
                    chunks = [rand_chunk() for _ in range(8)]
                    all_chunks.extend(chunks)
                    vdb.set_attribute(SpanAttributes.OUTPUT_VALUE, f"{len(chunks)} chunks retrieved")

                # Reranker
                with tracer.start_as_current_span(f"reranker-{i+1}") as rr:
                    rr.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.TOOL.value)
                    rr.set_attribute("reranker.model", "cohere-rerank-v3")
                    rr.set_attribute(SpanAttributes.INPUT_VALUE, f"{len(chunks)} chunks, query={sq[:40]}")
                    time.sleep(ms(random.randint(200, 400)))
                    top_chunks = chunks[:3]
                    rr.set_attribute(SpanAttributes.OUTPUT_VALUE, f"Top 3 chunks selected, scores: [0.94, 0.87, 0.81]")

        # Context assembly
        with tracer.start_as_current_span("context-assembler") as ca:
            ca.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.CHAIN.value)
            ca.set_attribute(SpanAttributes.INPUT_VALUE, f"{len(all_chunks)} total chunks from {len(sub_queries)} queries")
            time.sleep(ms(30))

            # Dedup step
            with tracer.start_as_current_span("dedup-chunks") as dd:
                dd.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.TOOL.value)
                dd.set_attribute(SpanAttributes.INPUT_VALUE, f"{len(all_chunks)} chunks")
                time.sleep(ms(15))
                dd.set_attribute(SpanAttributes.OUTPUT_VALUE, f"{len(all_chunks)-4} unique chunks after dedup")

            ca.set_attribute(SpanAttributes.OUTPUT_VALUE, "Context window: 12 chunks, ~3200 tokens")

        # Final generation
        with tracer.start_as_current_span("llm-generate") as gen:
            gen.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            gen.set_attribute(SpanAttributes.LLM_MODEL_NAME, "gpt-4o")
            gen.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 3856)
            gen.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 412)
            gen.set_attribute(SpanAttributes.INPUT_VALUE, f"[system prompt + {len(all_chunks)} chunks + user query]")
            time.sleep(ms(2400))
            gen.set_attribute(SpanAttributes.OUTPUT_VALUE,
                "RAG and fine-tuning are complementary approaches. RAG retrieves relevant context at inference time...")

        # Faithfulness check
        with tracer.start_as_current_span("faithfulness-eval") as fe:
            fe.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            fe.set_attribute(SpanAttributes.LLM_MODEL_NAME, "gpt-4o-mini")
            fe.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 1240)
            fe.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 45)
            time.sleep(ms(600))
            fe.set_attribute(SpanAttributes.OUTPUT_VALUE, '{"faithfulness": 0.91, "answer_relevance": 0.88}')

        root.set_attribute(SpanAttributes.OUTPUT_VALUE, "Final answer generated and validated")
    print("[RAG TRACE] Done")


# ─────────────────────────────────────────────
# TRACE 2: Multi-step agent with tool calls + loop
# ─────────────────────────────────────────────
def generate_agent_trace():
    task = "Research competitor pricing for Q3 report and summarize findings"
    print(f"\n[AGENT TRACE] Task: '{task}'")

    with tracer.start_as_current_span("research-agent") as root:
        root.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.AGENT.value)
        root.set_attribute(SpanAttributes.INPUT_VALUE, task)
        time.sleep(ms(30))

        # Planning step
        with tracer.start_as_current_span("plan") as plan:
            plan.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            plan.set_attribute(SpanAttributes.LLM_MODEL_NAME, "claude-3-5-sonnet")
            plan.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 512)
            plan.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 230)
            time.sleep(ms(1100))
            plan.set_attribute(SpanAttributes.OUTPUT_VALUE,
                "Plan: 1) web_search competitors, 2) scrape pricing pages, 3) extract prices, 4) summarize")

        # Loop: agent tries web search 3 times (simulating a retry loop — a real problem)
        for attempt in range(1, 4):
            with tracer.start_as_current_span(f"web-search-attempt-{attempt}") as ws:
                ws.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.TOOL.value)
                ws.set_attribute(SpanAttributes.INPUT_VALUE, f'web_search(query="SaaS competitor pricing 2025", attempt={attempt})')
                time.sleep(ms(random.randint(400, 900)))
                if attempt < 3:
                    ws.set_attribute(SpanAttributes.OUTPUT_VALUE, "rate_limited: 429 Too Many Requests")
                    ws.set_status(trace.StatusCode.ERROR)
                    ws.record_exception(Exception(f"RateLimitError on attempt {attempt}"))

                    # LLM decides to retry
                    with tracer.start_as_current_span(f"decide-retry-{attempt}") as dr:
                        dr.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
                        dr.set_attribute(SpanAttributes.LLM_MODEL_NAME, "claude-3-5-sonnet")
                        dr.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 380)
                        dr.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 42)
                        time.sleep(ms(700))
                        dr.set_attribute(SpanAttributes.OUTPUT_VALUE, f"Retrying web_search (attempt {attempt+1})")
                else:
                    ws.set_attribute(SpanAttributes.OUTPUT_VALUE,
                        "Results: [Competitor A: $49/mo, Competitor B: $99/mo, Competitor C: $29/mo]")

        # Scrape pricing pages
        companies = ["CompetitorA", "CompetitorB", "CompetitorC"]
        for company in companies:
            with tracer.start_as_current_span(f"scrape-{company.lower()}") as sc:
                sc.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.TOOL.value)
                sc.set_attribute(SpanAttributes.INPUT_VALUE, f'scrape_url(url="https://{company.lower()}.com/pricing")')
                time.sleep(ms(random.randint(300, 800)))
                if company == "CompetitorB":
                    # Simulate a timeout
                    sc.set_attribute(SpanAttributes.OUTPUT_VALUE, "TimeoutError: request timed out after 5000ms")
                    sc.set_status(trace.StatusCode.ERROR)
                    sc.record_exception(Exception("TimeoutError: 5000ms exceeded"))
                else:
                    sc.set_attribute(SpanAttributes.OUTPUT_VALUE,
                        f"{company} pricing: Starter $29, Pro $79, Enterprise custom")

        # Extract structured prices
        with tracer.start_as_current_span("extract-prices") as ep:
            ep.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            ep.set_attribute(SpanAttributes.LLM_MODEL_NAME, "claude-3-5-sonnet")
            ep.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 1840)
            ep.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 320)
            time.sleep(ms(1600))
            ep.set_attribute(SpanAttributes.OUTPUT_VALUE,
                '{"CompetitorA": {"starter": 29, "pro": 79}, "CompetitorB": null, "CompetitorC": {"starter": 19, "pro": 59}}')

        # Final summary
        with tracer.start_as_current_span("summarize") as sm:
            sm.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            sm.set_attribute(SpanAttributes.LLM_MODEL_NAME, "claude-3-5-sonnet")
            sm.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, 920)
            sm.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, 480)
            time.sleep(ms(1900))
            sm.set_attribute(SpanAttributes.OUTPUT_VALUE,
                "Q3 Competitor Pricing Summary: Market range $19-$99/mo. CompetitorB data missing due to scrape timeout.")

        root.set_attribute(SpanAttributes.OUTPUT_VALUE, "Report complete. Note: CompetitorB pricing unavailable.")
    print("[AGENT TRACE] Done")


if __name__ == "__main__":
    print("Generating synthetic traces for feasibility analysis...")
    generate_rag_trace()
    generate_agent_trace()
    time.sleep(2)  # flush
    print("\nAll traces sent to Phoenix at http://localhost:6006")
    print("Open Phoenix to inspect them.")
