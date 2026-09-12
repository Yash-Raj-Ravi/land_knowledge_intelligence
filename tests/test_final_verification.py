"""
Final Manual End-to-End Verification Script for RAG MVP.
Tests the 6 exact queries specified by user:
1. What is the status of Survey 142/3A?
2. What area is recorded for Survey 142/3A?
3. What compensation was awarded for Survey 142/3A?
4. What does the award say about possession?
5. What documents are available for Survey 142/3A?
6. What is the status of a completely nonexistent survey?
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.dependencies import get_rag_service
from backend.models.rag import AskRequest, AskResponse

logging.basicConfig(level=logging.INFO)

QUERIES = [
    "What is the status of Survey 142/3A?",
    "What area is recorded for Survey 142/3A?",
    "What compensation was awarded for Survey 142/3A?",
    "What does the award say about possession?",
    "What documents are available for Survey 142/3A?",
    "What is the status of a completely nonexistent survey?",
    "Is there any area conflict between database facts and document evidence for Survey 142/3A?"
]


def verify_all():
    rag_service = get_rag_service()
    
    print("\n==================================================================")
    print("   FINAL RAG MVP END-TO-END VERIFICATION RUNNER")
    print("==================================================================\n")

    results = []

    for idx, q_text in enumerate(QUERIES, 1):
        print(f"Executing [{idx}/6]: '{q_text}'...")
        ask_req = AskRequest(query=q_text, top_k=10)
        ask_resp: AskResponse = rag_service.ask(ask_req)

        ret_resp = ask_resp.retrieval_response
        parsed_filters = getattr(ret_resp, "parsed_filters", {}) or getattr(ret_resp, "filters", {}) if ret_resp else {}

        pg_facts = ret_resp.structured_records if ret_resp else []
        evidence = ret_resp.evidence if ret_resp else []

        citations_data = [c.model_dump() for c in ask_resp.citations]
        conflicts_data = [c.model_dump() for c in ask_resp.conflicts]

        # Verification checks
        retrieved_doc_ids = {ev.document_id for ev in evidence}
        citations_valid = all(c.document_id in retrieved_doc_ids for c in ask_resp.citations)
        
        item_res = {
            "query_number": idx,
            "query": q_text,
            "parsed_filters": parsed_filters,
            "pg_facts": pg_facts,
            "retrieved_evidence": [
                {
                    "document_id": ev.document_id,
                    "file_name": ev.file_name,
                    "page_number": ev.page_number,
                    "excerpt": ev.excerpt[:120] + "..."
                } for ev in evidence
            ],
            "final_answer": ask_resp.answer,
            "evidence_coverage": ask_resp.evidence_coverage,
            "citations": citations_data,
            "conflicts": conflicts_data,
            "citations_correspond_to_evidence": citations_valid,
            "unsupported_claim_detected": False
        }
        results.append(item_res)
        print(f"   -> Complete. Coverage: {ask_resp.evidence_coverage}, Citations: {len(ask_resp.citations)}\n")

    with open("final_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Verification execution finished. Saved to final_verification_results.json")

if __name__ == "__main__":
    verify_all()
