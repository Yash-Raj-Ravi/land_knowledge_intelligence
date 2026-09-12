"""
Fast Diagnostic Runner for Phase 3 Grounded RAG Pipeline.
Executes:
1. First Acceptance Test: "What is the status of Survey 142/3A?"
2. 3 Representative RAG Queries.

Measures exact timing breakdown per query:
- Retrieval Time
- Conflict Detection Time
- LLM Generation Time
- Total Time
"""

import sys
import os
import time
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.dependencies import (
    get_retrieval_service,
    get_conflict_detector,
    get_context_builder,
    get_llm_service
)
from backend.services.rag_service import RAGService
from backend.models.rag import AskRequest, AskResponse
from backend.models.retrieval import RetrievalRequest

logging.basicConfig(level=logging.INFO)

TARGET_QUERIES = [
    {
        "label": "FIRST ACCEPTANCE TEST",
        "query": "What is the status of Survey 142/3A?",
        "category": "survey_status"
    },
    {
        "label": "REPRESENTATIVE QUERY 1 (Numerical Area)",
        "query": "What is the area of Survey 142/3A in hectares?",
        "category": "numerical_area"
    },
    {
        "label": "REPRESENTATIVE QUERY 2 (Conflict Handling)",
        "query": "Is there a conflict between database values and document text for survey 142/3A?",
        "category": "conflict_handling"
    },
    {
        "label": "REPRESENTATIVE QUERY 3 (Insufficient Evidence)",
        "query": "What is the solar panel energy output for Survey 142/3A?",
        "category": "insufficient_evidence"
    }
]

def run_diagnostic():
    retrieval_service = get_retrieval_service()
    conflict_detector = get_conflict_detector()
    context_builder = get_context_builder()
    llm_service = get_llm_service()

    rag_service = RAGService(
        retrieval_service=retrieval_service,
        conflict_detector=conflict_detector,
        context_builder=context_builder,
        llm_service=llm_service
    )

    model_name = getattr(llm_service.llm_model, "model_name", "llama3.1:8b")

    print("\n==================================================")
    print("   PHASE 3 RAG FAST DIAGNOSTIC TEST RUNNER")
    print(f"   Model in Use: {model_name}")
    print("==================================================\n")

    report_items = []

    for idx, item in enumerate(TARGET_QUERIES, 1):
        q_label = item["label"]
        q_text = item["query"]
        category = item["category"]

        print(f"[{idx}/4] {q_label}")
        print(f"    Query: '{q_text}'")

        # Time Retrieval Phase
        t0 = time.time()
        retrieval_req = RetrievalRequest(query=q_text, top_k=10)
        ret_response = retrieval_service.retrieve(retrieval_req)
        t_retrieval = time.time() - t0

        # Time Conflict Detection & Context Building
        t1 = time.time()
        conflicts = conflict_detector.detect_conflicts(
            ret_response.structured_records or [],
            ret_response.evidence or []
        )
        ctx_str = context_builder.build_context(ret_response, conflicts)
        t_context = time.time() - t1

        # Time LLM Ask Execution
        t2 = time.time()
        ask_response: AskResponse = rag_service.ask(AskRequest(query=q_text, top_k=10))
        t_total = time.time() - t0
        t_llm = t_total - t_retrieval - t_context

        retrieval_ok = ret_response is not None and (len(ret_response.evidence) > 0 or len(ret_response.structured_records) > 0)
        llm_ok = ask_response is not None and bool(ask_response.answer)

        print(f"    -> Retrieval Complete: {retrieval_ok} ({t_retrieval*1000:.1f} ms, {len(ret_response.evidence)} doc chunks, {len(ret_response.structured_records)} DB recs)")
        print(f"    -> Conflict Detection & Context: {t_context*1000:.1f} ms ({len(conflicts)} conflicts found)")
        print(f"    -> LLM Generation Complete: {llm_ok} ({t_llm:.2f} s)")
        print(f"    -> Total Time: {t_total:.2f} s")
        print(f"    -> Evidence Coverage: {ask_response.evidence_coverage}")
        print(f"    -> Valid Citations Count: {len(ask_response.citations)}")
        print(f"    -> Answer Excerpt: {ask_response.answer[:120]}...\n")

        report_items.append({
            "label": q_label,
            "query": q_text,
            "model": model_name,
            "retrieval_time_ms": round(t_retrieval * 1000, 1),
            "llm_time_sec": round(t_llm, 2),
            "total_time_sec": round(t_total, 2),
            "retrieval_complete": retrieval_ok,
            "llm_complete": llm_ok,
            "coverage": ask_response.evidence_coverage,
            "citations": [c.model_dump() for c in ask_response.citations],
            "answer": ask_response.answer
        })

    with open("fast_diag_results.json", "w") as f:
        json.dump(report_items, f, indent=2)

    print("==================================================")
    print("   DIAGNOSTIC TEST SUMMARY REPORT")
    print("==================================================")
    print(f"{'Query Label':<38} {'Retrieval':<10} {'LLM Gen':<10} {'Total Time':<10}")
    print("-" * 72)
    for r in report_items:
        print(f"{r['label'][:36]:<38} {r['retrieval_time_ms']:>6.1f} ms {r['llm_time_sec']:>7.2f} s {r['total_time_sec']:>7.2f} s")
    print("==================================================\n")

if __name__ == "__main__":
    run_diagnostic()
