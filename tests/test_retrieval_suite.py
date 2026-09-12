import sys
import os
import tempfile
import logging
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services.query_parser import QueryParser
from backend.services.db_service import DatabaseService
from backend.vectorstore.chroma_store import ChromaStore
from backend.services.ranker import LandAcquisitionRanker
from backend.services.retrieval_service import RetrievalService
from backend.models.retrieval import RetrievalRequest
from backend.models.land_metadata import LandDocumentMetadata
from tests.benchmark_queries import BENCHMARK_QUERIES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RetrievalTestSuite")

class DummyEmbeddingService:
    """Deterministic Mock Embedding Service for isolated test suite."""
    def generate_query_embedding(self, query: str) -> List[float]:
        # Generate deterministic pseudo-embedding vector of size 384
        vec = [0.0] * 384
        q_lower = query.lower()
        if "142/3a" in q_lower or "142-3a" in q_lower:
            vec[0] = 1.0
            vec[1] = 0.5
        if "145/1" in q_lower or "145-1" in q_lower:
            vec[2] = 1.0
        if "hinjewadi" in q_lower:
            vec[10] = 1.0
        if "prj-nh44-exp" in q_lower or "nh44" in q_lower:
            vec[20] = 1.0
        if "award" in q_lower or "compensation" in q_lower:
            vec[30] = 1.0
        if "possession" in q_lower:
            vec[40] = 1.0
        if "wakad" in q_lower or "prj-mthl-002" in q_lower:
            vec[50] = 1.0
        return vec

def seed_isolated_test_data(store: ChromaStore, db_service: DatabaseService):
    """Seeds isolated test database fixtures without touching production data."""
    
    docs_fixtures = [
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_001_notification",
                source_file="doc_001_notification.pdf",
                document_category="Acquisition Notification",
                acquisition_stage="Section 11 Notification",
                project_id="PRJ-NH44-EXP",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Hinjewadi",
                survey_number="142/3A",
                survey_numbers=["142/3A", "145/1", "148/2"],
                document_date="2024-01-15",
                authority="SLAO Pune"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "GOVERNMENT OF MAHARASHTRA NOTIFICATION Section 11 under Land Acquisition Act for Project PRJ-NH44-EXP in Village Hinjewadi, Tehsil Mulshi, District Pune. Land parcels notified include Survey 142/3A (Area 1.2500 Ha), Survey 145/1 (Area 0.8500 Ha), and Survey 148/2 (Area 2.1000 Ha).",
                    "page_number": 1,
                    "section_heading": "Statutory Notification",
                    "survey_numbers": ["142/3A", "145/1", "148/2"]
                }
            ],
            "embeddings": [
                [1.0 if i in (0, 1, 10, 20) else 0.0 for i in range(384)]
            ]
        },
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_002_award",
                source_file="doc_002_award.pdf",
                document_category="Award",
                acquisition_stage="Award Declaration",
                project_id="PRJ-NH44-EXP",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Hinjewadi",
                survey_number="142/3A",
                survey_numbers=["142/3A"],
                document_date="2024-03-20",
                authority="SLAO Pune"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "FINAL SLAO AWARD STATEMENT for Project PRJ-NH44-EXP, Village Hinjewadi. Survey No. 142/3A total area 1.2500 Hectares. Determined total compensation awarded is Rs 45,000,000 (Forty-Five Lakhs INR) payable to Landowner Ramesh Patel.",
                    "page_number": 1,
                    "section_heading": "Award & Valuation",
                    "survey_numbers": ["142/3A"]
                }
            ],
            "embeddings": [
                [1.0 if i in (0, 1, 10, 20, 30) else 0.0 for i in range(384)]
            ]
        },
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_003_possession",
                source_file="doc_003_possession.pdf",
                document_category="Possession Record",
                acquisition_stage="Possession Taken",
                project_id="PRJ-NH44-EXP",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Hinjewadi",
                survey_number="142/3A",
                survey_numbers=["142/3A"],
                document_date="2024-05-15",
                authority="SLAO Pune"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "POSSESSION PANCHNAMA for Survey 142/3A Hinjewadi village under Project PRJ-NH44-EXP. Possession of 1.2500 Hectares taken over by National Highways Authority on 15th May 2024. Handover status is complete.",
                    "page_number": 1,
                    "section_heading": "Possession Receipt",
                    "survey_numbers": ["142/3A"]
                }
            ],
            "embeddings": [
                [1.0 if i in (0, 1, 10, 20, 40) else 0.0 for i in range(384)]
            ]
        },
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_004_khasra",
                source_file="doc_004_khasra.pdf",
                document_category="Land Record / Revenue Record",
                project_id="PRJ-NH44-EXP",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Hinjewadi",
                survey_number="145/1",
                survey_numbers=["145/1"],
                document_date="2023-11-10",
                authority="Tehsildar Mulshi"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "REVENUE LAND EXTRACT 7/12 for Survey 145/1 in Village Hinjewadi, Tehsil Mulshi. Total Area: 0.8500 Hectares. Land Category: Agricultural.",
                    "page_number": 1,
                    "section_heading": "7/12 Rights Extract",
                    "survey_numbers": ["145/1"]
                }
            ],
            "embeddings": [
                [1.0 if i in (2, 10) else 0.0 for i in range(384)]
            ]
        },
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_005_nh44_summary",
                source_file="doc_005_nh44_summary.pdf",
                document_category="Survey / Inspection Report",
                project_id="PRJ-NH44-EXP",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Hinjewadi",
                document_date="2024-02-01",
                authority="NHAI"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "PROJECT SUMMARY REPORT for Expressway Expansion Project PRJ-NH44-EXP. Total land required: 45.2 Hectares across Hinjewadi, Wakad, and Maan villages.",
                    "page_number": 1,
                    "section_heading": "Executive Summary",
                    "survey_numbers": []
                }
            ],
            "embeddings": [
                [1.0 if i in (10, 20) else 0.0 for i in range(384)]
            ]
        },
        {
            "metadata": LandDocumentMetadata(
                document_id="doc_006_wakad_notification",
                source_file="doc_006_wakad_notification.pdf",
                document_category="Acquisition Notification",
                acquisition_stage="Section 4 Preliminary Notification",
                project_id="PRJ-MTHL-002",
                state="Maharashtra",
                district="Pune",
                tehsil="Mulshi",
                village="Wakad",
                survey_number="88/1B",
                survey_numbers=["88/1B"],
                document_date="2024-04-10",
                authority="SLAO Pune"
            ),
            "chunks": [
                {
                    "chunk_id": 1,
                    "text": "SECTION 4 PRELIMINARY NOTIFICATION for Project PRJ-MTHL-002 in Wakad Village. Land Parcel Gat No. 88/1B area 0.5000 Hectares proposed for acquisition.",
                    "page_number": 1,
                    "section_heading": "Preliminary Notification",
                    "survey_numbers": ["88/1B"]
                }
            ],
            "embeddings": [
                [1.0 if i in (50,) else 0.0 for i in range(384)]
            ]
        }
    ]

    for item in docs_fixtures:
        store.add_land_chunk_embeddings(
            chunks=item["chunks"],
            embeddings=item["embeddings"],
            doc_metadata=item["metadata"],
            file_path=f"/mock/paths/{item['metadata'].source_file}"
        )

    # Seed structured PostgreSQL records in test db_service memory store
    structured_data = [
        {
            "survey_number": "142/3A",
            "village": "Hinjewadi",
            "tehsil": "Mulshi",
            "district": "Pune",
            "state": "Maharashtra",
            "project_id": "PRJ-NH44-EXP",
            "parcel_id": "PCL-VIL-PUNE-MULSHI-HINJEWADI-142/3A",
            "area_hectares": 1.2500,
            "land_category": "Agricultural",
            "acquisition_status": "Awarded / Possession Taken",
            "total_award_amount": 4500000.0,
            "payment_status": "Awarded",
            "landowner": "Ramesh Patel"
        },
        {
            "survey_number": "145/1",
            "village": "Hinjewadi",
            "tehsil": "Mulshi",
            "district": "Pune",
            "state": "Maharashtra",
            "project_id": "PRJ-NH44-EXP",
            "parcel_id": "PCL-VIL-PUNE-MULSHI-HINJEWADI-145/1",
            "area_hectares": 0.8500,
            "land_category": "Agricultural",
            "acquisition_status": "Section 11 Notified",
            "total_award_amount": None,
            "payment_status": "Pending",
            "landowner": "Suresh Deshmukh"
        },
        {
            "survey_number": "88/1B",
            "village": "Wakad",
            "tehsil": "Mulshi",
            "district": "Pune",
            "state": "Maharashtra",
            "project_id": "PRJ-MTHL-002",
            "parcel_id": "PCL-VIL-PUNE-MULSHI-WAKAD-88/1B",
            "area_hectares": 0.5000,
            "land_category": "Residential",
            "acquisition_status": "Section 4 Notified",
            "total_award_amount": None,
            "payment_status": "Pending",
            "landowner": "Vikas Shinde"
        }
    ]

    for sp in structured_data:
        db_service.persist_structured_parcels(
            meta=LandDocumentMetadata(
                document_id="mock_doc",
                source_file="mock.pdf",
                document_category="Land Record / Revenue Record",
                village=sp["village"],
                district=sp["district"],
                tehsil=sp["tehsil"],
                state=sp["state"],
                project_id=sp["project_id"]
            ),
            structured_parcels=[sp],
            file_path="/mock/paths/mock.pdf"
        )

def run_smoke_tests(retrieval_service: RetrievalService):
    """Executes the 10 Functional Smoke Test Queries and prints full retrieval trace."""
    logger.info("\n" + "="*80)
    logger.info("  RUNNING 10 FUNCTIONAL SMOKE TEST QUERIES")
    logger.info("="*80 + "\n")

    smoke_queries = [
        "What is the status of Survey 142/3A?",
        "What is the area of Survey 142/3A?",
        "What compensation was awarded for Survey 142/3A?",
        "What documents are available for Survey 142/3A?",
        "Show acquisition documents for Hinjewadi village.",
        "Find documents for Project PRJ-NH44-EXP.",
        "What notification was issued for this project?",
        "What does the award say about possession?",
        "List all parcels under Project PRJ-NH44-EXP",
        "What is the status of Survey 999/999 in Nonexistent Village?"
    ]

    passed_count = 0
    for idx, query in enumerate(smoke_queries, 1):
        req = RetrievalRequest(query=query, top_k=5)
        res = retrieval_service.retrieve(req)

        logger.info(f"SMOKE TEST #{idx}: '{query}'")
        logger.info(f"  Parsed Filters:    {res.parsed_filters}")
        logger.info(f"  Applied Filters:   {res.applied_filters}")
        logger.info(f"  PG Records:        {len(res.structured_records)} records returned")
        if res.structured_records:
            logger.info(f"                     {res.structured_records[0]}")
        logger.info(f"  Chroma Candidates: {res.candidate_count}")
        logger.info(f"  Retrieved Chunks:  {res.retrieved_count} (Distance Metric: {res.distance_metric})")
        logger.info(f"  Ranking Method:    {res.ranking_method}")
        logger.info(f"  Evidence Coverage: {res.evidence_coverage}")
        logger.info(f"  Evidence Count:    {len(res.evidence)}")

        if idx in (1, 2, 3, 4): # Survey 142/3A queries
            assert res.parsed_filters.get("normalized_survey_number") == "142/3A", f"Test {idx} failed survey parse"
            assert len(res.evidence) > 0 or len(res.structured_records) > 0, f"Test {idx} returned zero evidence"
        elif idx in (5,): # Hinjewadi village
            assert res.parsed_filters.get("village") == "Hinjewadi", f"Test {idx} failed village parse"
        elif idx in (6, 9): # Project PRJ-NH44-EXP
            assert res.parsed_filters.get("project_id") == "PRJ-NH44-EXP", f"Test {idx} failed project parse"
        elif idx == 7:
            assert res.parsed_filters.get("document_category") == "Acquisition Notification", f"Test {idx} failed category parse"
        elif idx == 8:
            assert res.parsed_filters.get("document_category") == "Award", f"Test {idx} failed category parse"
        elif idx == 10: # No match
            assert res.evidence_coverage == "INSUFFICIENT" or len(res.evidence) == 0, f"Test 10 expected insufficient coverage"

        passed_count += 1
        logger.info(f"  Status: PASSED [Coverage: {res.evidence_coverage}]\n" + "-"*60)

    logger.info(f"\n Smoke Tests Completed: {passed_count}/10 PASSED SUCCESSFULLY.\n")

def run_30_query_benchmark(retrieval_service: RetrievalService):
    """Executes 30-Query Gold-Standard Benchmark and computes Hit@5, Precision@5, Recall@5."""
    logger.info("\n" + "="*80)
    logger.info("  RUNNING 30-QUERY GOLD-STANDARD RETRIEVAL BENCHMARK")
    logger.info("="*80 + "\n")

    hits_at_5 = 0
    total_precision = 0.0
    total_recall = 0.0
    valid_recall_queries = 0

    for q_item in BENCHMARK_QUERIES:
        q_id = q_item["id"]
        query = q_item["query"]
        expected_docs = set(q_item.get("expected_doc_ids", []))

        req = RetrievalRequest(query=query, top_k=5)
        res = retrieval_service.retrieve(req)

        retrieved_docs = set(ev.document_id for ev in res.evidence)

        if len(expected_docs) == 0:
            # No-match / empty expected query handling
            is_hit = 1 if len(retrieved_docs) == 0 or res.evidence_coverage == "INSUFFICIENT" else 0
            precision = 1.0 if is_hit else 0.0
            recall = 1.0 if is_hit else 0.0
        else:
            intersection = retrieved_docs.intersection(expected_docs)
            is_hit = 1 if len(intersection) > 0 else 0
            precision = len(intersection) / 5.0 # Precision@5
            recall = len(intersection) / float(len(expected_docs)) # Recall@5
            valid_recall_queries += 1

        hits_at_5 += is_hit
        total_precision += precision
        total_recall += recall

        logger.info(f"BENCHMARK Q{q_id:02d} [{q_item['category']}]: '{query}'")
        logger.info(f"  Target Docs:    {list(expected_docs)}")
        logger.info(f"  Retrieved Docs: {list(retrieved_docs)}")
        logger.info(f"  Hit@5: {is_hit} | Precision@5: {precision:.2f} | Recall@5: {recall:.2f}\n")

    num_q = len(BENCHMARK_QUERIES)
    avg_hit_at_5 = hits_at_5 / float(num_q)
    avg_precision = total_precision / float(num_q)
    avg_recall = total_recall / float(num_q)

    logger.info("="*80)
    logger.info("  PHASE 2 RETRIEVAL BENCHMARK RESULTS SUMMARY")
    logger.info("="*80)
    logger.info(f"  Total Benchmark Queries : {num_q}")
    logger.info(f"  Hit@5                   : {avg_hit_at_5 * 100:.2f}% ({hits_at_5}/{num_q})")
    logger.info(f"  Precision@5             : {avg_precision * 100:.2f}%")
    logger.info(f"  Recall@5                : {avg_recall * 100:.2f}%")
    logger.info("="*80 + "\n")

    return {
        "total_queries": num_q,
        "hit_at_5": avg_hit_at_5,
        "precision_at_5": avg_precision,
        "recall_at_5": avg_recall
    }

def main():
    # Create isolated temporary directory for ChromaDB test fixture
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        logger.info(f"Created isolated test directory for ChromaDB: {temp_dir}")

        store = ChromaStore(chroma_path=temp_dir, collection_name="isolated_test_collection")
        db_service = DatabaseService() # Uses in-memory fallback
        query_parser = QueryParser()
        embedding_service = DummyEmbeddingService()
        ranker = LandAcquisitionRanker()

        # Seed isolated fixtures
        seed_isolated_test_data(store, db_service)

        retrieval_service = RetrievalService(
            query_parser=query_parser,
            embedding_service=embedding_service,
            db_service=db_service,
            store=store,
            ranker=ranker
        )

        # 1. Run 10 Functional Smoke Tests
        run_smoke_tests(retrieval_service)

        # 2. Run 30-Query Benchmark Suite
        benchmark_results = run_30_query_benchmark(retrieval_service)

if __name__ == "__main__":
    main()

