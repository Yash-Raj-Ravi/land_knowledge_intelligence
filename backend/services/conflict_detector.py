import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ConflictItem(BaseModel):
    field_name: str
    authoritative_value: str
    document_value: str
    document_id: str
    file_name: str
    page_number: int
    conflict_type: str = "Numerical Discrepancy"

class ConflictDetector:
    """
    Deterministic Conflict Detector.
    Compares authoritative PostgreSQL facts against document text evidence.
    """

    def detect_conflicts(
        self,
        structured_records: List[Dict[str, Any]],
        evidence_list: List[Any]
    ) -> List[ConflictItem]:
        conflicts: List[ConflictItem] = []

        if not structured_records or not evidence_list:
            return conflicts

        for pg_rec in structured_records:
            s_num = pg_rec.get("survey_number")
            if not s_num:
                continue

            pg_area = pg_rec.get("area_hectares")
            pg_award = pg_rec.get("total_award_amount")
            pg_status = pg_rec.get("acquisition_status")

            # Check each evidence source for potential discrepancies
            for ev in evidence_list:
                ev_survey = getattr(ev, "survey_number", None) or getattr(ev, "raw_survey_number", None)
                ev_text = getattr(ev, "excerpt", "")
                doc_id = getattr(ev, "document_id", "unknown")
                file_name = getattr(ev, "file_name", "document.pdf")
                page_num = getattr(ev, "page_number", 1)

                # 1. Area Discrepancy Check
                if pg_area is not None:
                    # Look for area numbers in chunk text (e.g. "area 1.5000 ha" or "area 0.52 ha")
                    area_matches = re.findall(
                        r"(?:area|extent)\s*(?:is|of)?\s*:?\s*([0-9]+\.?[0-9]*)\s*(?:ha|hectare|acres)?",
                        ev_text,
                        re.IGNORECASE
                    )
                    for match_val in area_matches:
                        try:
                            doc_area = float(match_val)
                            # If survey matches or chunk explicitly mentions target survey
                            if s_num.lower() in ev_text.lower() or (ev_survey and s_num.lower() in ev_survey.lower()):
                                if abs(doc_area - float(pg_area)) > 0.05: # > 0.05 Ha difference threshold
                                    conflicts.append(ConflictItem(
                                        field_name="area_hectares",
                                        authoritative_value=f"{pg_area:.4f} Ha",
                                        document_value=f"{doc_area:.4f} Ha",
                                        document_id=doc_id,
                                        file_name=file_name,
                                        page_number=page_num,
                                        conflict_type="Numerical Discrepancy (Area)"
                                    ))
                        except ValueError:
                            pass

                # 2. Compensation Award Discrepancy Check
                if pg_award is not None:
                    award_matches = re.findall(
                        r"(?:rs|₹|amount|compensation|awarded)\s*:?\s*(?:rs|₹)?\s*([0-9,]+)",
                        ev_text,
                        re.IGNORECASE
                    )
                    for match_val in award_matches:
                        clean_num = match_val.replace(",", "")
                        try:
                            doc_award = float(clean_num)
                            if doc_award > 1000 and s_num.lower() in ev_text.lower():
                                if abs(doc_award - float(pg_award)) > 1000: # > Rs 1,000 difference
                                    conflicts.append(ConflictItem(
                                        field_name="total_award_amount",
                                        authoritative_value=f"₹{pg_award:,.2f}",
                                        document_value=f"₹{doc_award:,.2f}",
                                        document_id=doc_id,
                                        file_name=file_name,
                                        page_number=page_num,
                                        conflict_type="Numerical Discrepancy (Compensation)"
                                    ))
                        except ValueError:
                            pass

        return conflicts
