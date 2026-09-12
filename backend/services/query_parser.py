import re
from typing import Dict, Any, Optional, Tuple
from backend.models.land_metadata import sanitize_survey_number, DocumentCategoryEnum

def parse_survey_number(raw_query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts (raw_survey_number, normalized_survey_number).
    Preserves exact legal identifier structure without over-normalization.
    """
    patterns = [
        r"(?:Survey\s*(?:No\.?|#)?|S\.?\s*No\.?|Gat\s*(?:No\.?|#)?|Khasra\s*(?:No\.?|#)?|Plot\s*(?:No\.?|#)?)\s*:?\s*([A-Za-z0-9\/\-]+)",
        r"(?:Gat|Khasra|Survey|Plot)\s+([0-9]+\/[0-9]+[A-Za-z]?|[0-9]+)",
        r"\b([0-9]{1,4}[\/\-][0-9]{1,3}[A-Za-z]{0,2})\b"
    ]
    for pat in patterns:
        match = re.search(pat, raw_query, re.IGNORECASE)
        if match:
            raw_val = match.group(1).strip()
            norm_val = raw_val.replace("-", "/")
            san = sanitize_survey_number(norm_val)
            if san:
                return raw_val, san
    return None, None

def normalize_survey_number_query(raw_query: str) -> Optional[str]:
    _, norm_s = parse_survey_number(raw_query)
    return norm_s

class QueryParser:
    """
    Deterministic Query Parser for Land Acquisition Queries.
    Phase 2: Uses pure regex and pattern matching without LLM calls.
    """
    def __init__(self, llm_model: Any = None):
        self.llm_model = llm_model

    def parse_query_filters(self, query: str) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        q_lower = query.lower()

        # 1. Survey Number Extraction (Raw & Normalized)
        raw_s, norm_s = parse_survey_number(query)
        if norm_s:
            filters["raw_survey_number"] = raw_s
            filters["normalized_survey_number"] = norm_s
            filters["survey_number"] = norm_s

        # 2. Project ID Extraction
        prj_match = re.search(r"(?:Project|PRJ)\s*:?\s*([A-Za-z0-9\-_]+)", query, re.IGNORECASE)
        if not prj_match:
            prj_match = re.search(r"\b(PRJ-[A-Z0-9\-_]+)\b", query, re.IGNORECASE)
        if prj_match:
            filters["project_id"] = prj_match.group(1).strip().upper()

        # 3. Parcel ID Extraction
        pcl_match = re.search(r"\b(PCL-[A-Z0-9\-_]+)\b", query, re.IGNORECASE)
        if pcl_match:
            filters["parcel_id"] = pcl_match.group(1).strip().upper()

        # 4. Document Category & Acquisition Stage Extraction
        if any(k in q_lower for k in ["notification", "section 4", "section 11", "section 19"]):
            filters["document_category"] = DocumentCategoryEnum.NOTIFICATION.value
            if "section 4" in q_lower:
                filters["acquisition_stage"] = "Section 4 Preliminary Notification"
            elif "section 11" in q_lower:
                filters["acquisition_stage"] = "Section 11 Notification"
            elif "section 19" in q_lower:
                filters["acquisition_stage"] = "Section 19 Declaration"
        elif any(k in q_lower for k in ["award", "slao award", "valuation"]):
            filters["document_category"] = DocumentCategoryEnum.AWARD.value
            filters["acquisition_stage"] = "Award Declaration"
        elif any(k in q_lower for k in ["compensation", "payout", "disbursement", "paid"]):
            filters["document_category"] = DocumentCategoryEnum.COMPENSATION.value
        elif any(k in q_lower for k in ["possession", "panchnama", "handover"]):
            filters["document_category"] = DocumentCategoryEnum.POSSESSION.value
            filters["acquisition_stage"] = "Possession Taken"
        elif any(k in q_lower for k in ["7/12", "khasra", "revenue record", "land record"]):
            filters["document_category"] = DocumentCategoryEnum.LAND_RECORD.value

        # 5. Village Extraction
        vil_match = re.search(r"(?:Village|Mauza|Mouza|मौजे)\s*:?\s*([A-Za-z]+)", query, re.IGNORECASE)
        if not vil_match:
            vil_match = re.search(r"([A-Za-z]+)\s+(?:village|mauza|mouza)", query, re.IGNORECASE)
        if vil_match:
            filters["village"] = vil_match.group(1).strip().title()
        elif "hinjewadi" in q_lower:
            filters["village"] = "Hinjewadi"
        elif "wakad" in q_lower:
            filters["village"] = "Wakad"
        elif "maan" in q_lower:
            filters["village"] = "Maan"

        # 6. District Extraction
        dis_match = re.search(r"(?:District|Dist\.?)\s*:?\s*([A-Za-z]+)", query, re.IGNORECASE)
        if dis_match:
            filters["district"] = dis_match.group(1).strip().title()
        elif "pune" in q_lower:
            filters["district"] = "Pune"
        elif "thane" in q_lower:
            filters["district"] = "Thane"

        # 7. Tehsil Extraction
        teh_match = re.search(r"(?:Tehsil|Taluka)\s*:?\s*([A-Za-z]+)", query, re.IGNORECASE)
        if teh_match:
            filters["tehsil"] = teh_match.group(1).strip().title()
        elif "mulshi" in q_lower:
            filters["tehsil"] = "Mulshi"

        # 8. State Extraction
        if "maharashtra" in q_lower:
            filters["state"] = "Maharashtra"

        # 9. Document Date / Year Extraction
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", query)
        if year_match:
            filters["document_date"] = year_match.group(1)

        # Indicate whether a reliable metadata filter was identified
        reliable_keys = {
            "survey_number", "normalized_survey_number", "project_id",
            "parcel_id", "village", "document_category", "district"
        }
        filters["has_reliable_filter"] = any(k in filters for k in reliable_keys)

        return filters

