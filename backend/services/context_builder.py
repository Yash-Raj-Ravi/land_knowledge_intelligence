import logging
from typing import List, Dict, Any, Optional
from backend.models.retrieval import RetrievalResponse
from backend.services.conflict_detector import ConflictItem

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    Constructs structured, grounded prompt contexts from Phase 2 RetrievalResponse
    and deterministic ConflictItems.
    """

    def build_context(
        self,
        retrieval_response: RetrievalResponse,
        conflicts: Optional[List[ConflictItem]] = None
    ) -> str:
        lines = []

        # 1. Evidence Coverage Header
        coverage = retrieval_response.evidence_coverage
        lines.append(f"EVIDENCE COVERAGE STATUS: {coverage}")
        lines.append("=" * 60)

        # 2. Authoritative PostgreSQL Database Facts
        lines.append("\n[AUTHORITATIVE DATABASE FACTS]")
        if retrieval_response.structured_records:
            for idx, rec in enumerate(retrieval_response.structured_records, 1):
                lines.append(f"Record {idx}:")
                for k, v in rec.items():
                    if v is not None:
                        lines.append(f"  - {k}: {v}")
        else:
            lines.append("No matching authoritative database records found in PostgreSQL.")

        # 3. Explicit Detected Conflicts
        lines.append("\n[DETECTED CONFLICTS BETWEEN DB & DOCUMENTS]")
        if conflicts:
            for idx, cfl in enumerate(conflicts, 1):
                lines.append(f"Conflict {idx}:")
                lines.append(f"  - Field: {cfl.field_name}")
                lines.append(f"  - Authoritative Value (PostgreSQL): {cfl.authoritative_value}")
                lines.append(f"  - Document Value: {cfl.document_value}")
                lines.append(f"  - Source Document: {cfl.file_name} (Doc ID: {cfl.document_id}, Page {cfl.page_number})")
                lines.append(f"  - Type: {cfl.conflict_type}")
        else:
            lines.append("No explicit factual discrepancies detected between Database and Document Evidence.")

        # 4. Retrieved Document Evidence
        if retrieval_response.evidence:
            distinct_docs = len({ev.document_id for ev in retrieval_response.evidence})
            lines.append(f"\n[DOCUMENT EVIDENCE ({distinct_docs} Distinct Document(s), {len(retrieval_response.evidence)} Excerpt Chunk(s))]")
            for idx, ev in enumerate(retrieval_response.evidence, 1):
                lines.append(f"Source Excerpt {idx} (Page {ev.page_number} of {ev.file_name}):")

                lines.append(f"  - Document ID: {ev.document_id}")
                lines.append(f"  - File Name: {ev.file_name}")
                lines.append(f"  - Page Number: {ev.page_number}")
                lines.append(f"  - Section Heading: {ev.section_heading}")
                lines.append(f"  - Chunk ID: {ev.chunk_id}")
                if ev.survey_number:
                    lines.append(f"  - Survey Number: {ev.survey_number}")
                if ev.project_id:
                    lines.append(f"  - Project ID: {ev.project_id}")
                lines.append(f"  - Text Excerpt: \"{ev.excerpt.strip()}\"")
                lines.append("-" * 40)
        else:
            lines.append("No relevant document text chunks retrieved.")

        return "\n".join(lines)
