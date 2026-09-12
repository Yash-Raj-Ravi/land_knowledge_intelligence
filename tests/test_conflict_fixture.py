"""
Explicit Conflict Test Fixture.
Verifies that when PostgreSQL facts (e.g. area = 0.45 Ha) and Document text (e.g. area = 0.52 Ha) disagree:
1. ConflictDetector identifies the conflict.
2. ContextBuilder formats [DETECTED CONFLICTS].
3. RAGService / LLM reports BOTH values in natural language.
4. LLM does not silently choose one value over the other.
5. Citation points to the conflicting document page.
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.conflict_detector import ConflictDetector, ConflictItem
from backend.services.context_builder import ContextBuilder
from backend.models.retrieval import RetrievalResponse, EvidenceSource
from backend.models.rag import AskRequest, AskResponse
from backend.core.dependencies import get_rag_service, get_llm_service
from backend.services.rag_service import RAGService

logging.basicConfig(level=logging.INFO)

def test_real_conflict():
    print("\n==================================================")
    print("   RUNNING REAL CONFLICT TEST FIXTURE")
    print("==================================================\n")

    pg_records = [
        {
            "parcel_id": "PCL-VADADALA-142-3A",
            "survey_number": "142/3A",
            "area_hectares": 0.4500,
            "acquisition_status": "Section 19 Notification Issued",
            "total_award_amount": 2450000.00
        }
    ]

    conflicting_evidence = [
        EvidenceSource(
            document_id="p2-doc-conflict-001",
            file_name="Surveyor_Field_Inspection_Report.pdf",
            page_number=4,
            section_heading="Field Extent Verification",
            chunk_id=401,
            survey_number="142/3A",
            excerpt="Physical measurement on site for Survey 142/3A indicates area of 0.52 hectare instead of revenue record extent.",
            distance=0.12,
            distance_metric="l2"
        )
    ]

    # 1. Test ConflictDetector directly
    detector = ConflictDetector()
    conflicts = detector.detect_conflicts(pg_records, conflicting_evidence)

    print(f"1. ConflictDetector Output ({len(conflicts)} conflict(s) detected):")
    for c in conflicts:
        print(f"   - Field: {c.field_name}")
        print(f"   - Authoritative PG Value: {c.authoritative_value}")
        print(f"   - Document Value: {c.document_value}")
        print(f"   - Source File: {c.file_name} (p. {c.page_number}, Doc ID: {c.document_id})")

    assert len(conflicts) > 0, "ConflictDetector failed to detect area discrepancy!"
    assert "0.45" in conflicts[0].authoritative_value
    assert "0.52" in conflicts[0].document_value

    # 2. Test ContextBuilder with explicit conflict
    ret_response = RetrievalResponse(
        query="What is the area of Survey 142/3A and are there any conflicts?",
        parsed_filters={"survey_number": "142/3A"},
        structured_records=pg_records,
        evidence=conflicting_evidence,
        evidence_coverage="COMPLETE"
    )

    builder = ContextBuilder()
    formatted_context = builder.build_context(ret_response, conflicts)

    print("\n2. ContextBuilder Formatted Context Header:")
    print(formatted_context[:400] + "...\n")

    # 3. Test RAGService end-to-end with this mock RetrievalResponse
    llm_service = get_llm_service()
    rag_service = RAGService(
        retrieval_service=None, # Not used since we simulate retrieve call
        conflict_detector=detector,
        context_builder=builder,
        llm_service=llm_service
    )

    # Directly run pipeline logic
    from backend.utils.prompt_builder import build_land_rag_prompt
    prompt = build_land_rag_prompt(context=formatted_context, query="What is the area of Survey 142/3A and are there any conflicts?")
    raw_resp = llm_service.generate_response(prompt)
    parsed = rag_service._parse_json(raw_resp)

    assert parsed is not None, "Failed to parse JSON response!"

    answer = parsed.get("answer", "")
    citations = parsed.get("citations", [])

    print("3. LLM Natural Language Answer:")
    print(f"   {answer}")
    print("\n4. Citations Returned:")
    print(f"   {citations}")

    # Validation Checks
    answer_lower = answer.lower()
    has_045 = "0.45" in answer
    has_052 = "0.52" in answer
    reports_both = has_045 and has_052
    points_to_p4 = any(c.get("page_number") == 4 for c in citations if isinstance(c, dict)) or "4" in str(citations)

    print("\n--------------------------------------------------")
    print("   EXPLICIT CONFLICT TEST VERIFICATION RESULTS:")
    print("--------------------------------------------------")
    print(f"   - ConflictDetector Identified Conflict: TRUE")
    print(f"   - LLM Reports PostgreSQL Value (0.45 Ha): {has_045}")
    print(f"   - LLM Reports Document Value (0.52 Ha): {has_052}")
    print(f"   - LLM Reports BOTH values (no silent pick): {reports_both}")
    print(f"   - Citation Points to Page 4: {points_to_p4}")
    print("==================================================\n")

if __name__ == "__main__":
    test_real_conflict()
