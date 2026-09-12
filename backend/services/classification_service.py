import re
import json
import logging
from typing import Dict, Any, List, Optional
from backend.models.land_metadata import LandDocumentMetadata, DocumentCategoryEnum, sanitize_survey_number

logger = logging.getLogger(__name__)

# Deterministic Regex Patterns for P0 Fixes
PROJECT_PATTERNS = [
    r"(?:Project\s*Code|Project\s*ID|Project\s*Name|Project|प्रकल्प|परियोजना)\s*:?\s*([A-Za-z0-9\-_]+)",
]

STATE_PATTERNS = [
    r"(?:State\s*Name|State|राज्य)\s*:?\s*([A-Za-z\s]+?)(?:,|\.|\n|District|Tehsil|जिल्हा)",
]

SURVEY_PATTERNS = [
    r"(?:Survey|S\.?\s*No\.?|Gat\s*No\.?|Khasra\s*No\.?|Plot\s*No\.?|गट\s*क्रमांक|गट\s*क्र|सर्व्हे\s*क्र|खसरा\s*नं)\s*:?\s*([A-Za-z0-9\/\-]+)",
    r"(?:Gat|Khasra|Survey)\s+([0-9]+\/[0-9]+[A-Za-z]?|[0-9]+)"
]

VILLAGE_PATTERNS = [
    r"(?:Village|Mauza|Mouza|मौजे|गाव|ग्राम)\s*:?\s*([A-Za-z\s\u0900-\u097F]+?)(?:,|\.|\n|Tehsil|Taluka|District|तालुका|जिल्हा)",
]

TEHSIL_PATTERNS = [
    r"(?:Tehsil|Taluka|Tahsil|तालुका|तहसील)\s*:?\s*([A-Za-z\s\u0900-\u097F]+?)(?:,|\.|\n|District|State|जिल्हा|राज्य)",
]

DISTRICT_PATTERNS = [
    r"(?:District|Dist\.?|जिल्हा|जिला)\s*:?\s*([A-Za-z\s\u0900-\u097F]+?)(?:,|\.|\n|State|राज्य)",
]

SECTION_PATTERNS = [
    r"(Section\s+(?:4|11(?:\(1\))?|19(?:\(1\)|\(2\))?|30|64)|RFCTLARR\s+Act|Land\s+Acquisition\s+Act|कलम\s+(?:४|११|१९|३०))"
]


DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b"
]

CATEGORY_KEYWORDS = {
    DocumentCategoryEnum.LAND_RECORD.value: ["7/12", "khasra", "khatoni", "jamabandi", "rights record", "title search", "khatedar"],
    DocumentCategoryEnum.NOTIFICATION.value: ["section 4", "section 11", "section 19", "preliminary notification", "gazette", "declaration"],
    DocumentCategoryEnum.AWARD.value: ["slao award", "valuation award", "compensation award", "collector award", "solatium"],
    DocumentCategoryEnum.COMPENSATION.value: ["disbursement", "payment voucher", "compensation register", "payout matrix"],
    DocumentCategoryEnum.RR_RECORD.value: ["rehabilitation", "resettlement", "r&r", "displaced family", "land loser"],
    DocumentCategoryEnum.POSSESSION.value: ["panchnama", "possession certificate", "handover", "form e", "taken possession"],
    DocumentCategoryEnum.GOVT_ORDER.value: ["government order", "sanction", "approval", "cabinet", "noc"],
    DocumentCategoryEnum.SURVEY_REPORT.value: ["joint measurement", "jms", "spot inspection", "survey report", "field boundary"],
    DocumentCategoryEnum.LEGAL_DISPUTE.value: ["writ petition", "court order", "stay order", "litigation", "high court"]
}

def normalize_text_value(val: Optional[str]) -> Optional[str]:
    if not val or not isinstance(val, str):
        return None
    val_clean = val.strip().strip(".,;:()")
    if not val_clean or val_clean.lower() in ("none", "null", "unknown", "n/a"):
        return None
    return val_clean

class ClassificationService:
    def __init__(self, llm_model: Any = None):
        self.llm_model = llm_model

    def extract_deterministic_metadata(self, text: str) -> Dict[str, Any]:
        extracted = {}

        # 1. Project ID
        for pat in PROJECT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                prj = normalize_text_value(match.group(1))
                if prj and len(prj) >= 2:
                    extracted["project_id"] = prj.upper()
                    break

        # 2. State
        for pat in STATE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                st = normalize_text_value(match.group(1))
                if st and len(st) >= 2:
                    extracted["state"] = st.title()
                    break

        # 3. Survey Numbers (Full set, non-truncated)
        surveys = set()
        for pat in SURVEY_PATTERNS:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                clean_m = sanitize_survey_number(m)
                if clean_m:
                    surveys.add(clean_m)
        if surveys:
            sorted_surveys = sorted(list(surveys))
            extracted["survey_numbers"] = sorted_surveys
            extracted["survey_number"] = sorted_surveys[0]

        # 4. Village
        for pat in VILLAGE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                v = normalize_text_value(match.group(1))
                if v and len(v) >= 2:
                    extracted["village"] = v.title()
                    break

        # 5. Tehsil
        for pat in TEHSIL_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                t = normalize_text_value(match.group(1))
                if t and len(t) >= 2:
                    extracted["tehsil"] = t.title()
                    break

        # 6. District
        for pat in DISTRICT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                d = normalize_text_value(match.group(1))
                if d and len(d) >= 2:
                    extracted["district"] = d.title()
                    break

        # 7. Section / Stage
        for pat in SECTION_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                extracted["acquisition_stage"] = match.group(1).strip()
                break

        # 8. Date
        for pat in DATE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                extracted["document_date"] = match.group(1).strip()
                break

        # 9. Category Hint
        text_lower = text[:3000].lower()
        matched_categories = []
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    matched_categories.append(category)
                    break
        if len(matched_categories) == 1:
            extracted["document_category_hint"] = matched_categories[0]

        return extracted

    def classify_and_extract_llm(self, text_sample: str) -> Dict[str, Any]:
        if not self.llm_model:
            return {}

        prompt = f"""
You are a Land Acquisition Legal Document Classifier.
Analyze the following document text excerpt and extract metadata.

Return ONLY valid JSON with exactly these keys:
{{
  "document_category": "One of: Land Record / Revenue Record, Acquisition Notification, Award, Compensation Record, R&R Record, Possession Record, Government Order / Approval, Survey / Inspection Report, Legal / Dispute Document",
  "project_id": "Project code or name if mentioned, otherwise null",
  "authority": "Issuing authority (e.g. SLAO Unit 2, District Collector), otherwise null",
  "language": "English, Hindi, or Marathi"
}}

Rules:
- Do not invent facts.
- Choose document_category strictly from the 9 options.
- Return ONLY JSON.

Document Excerpt:
{text_sample[:2500]}
"""
        try:
            response = self.llm_model.generate(prompt)
            clean_json = re.sub(r"^```json\s*", "", response.strip(), flags=re.IGNORECASE)
            clean_json = re.sub(r"```$", "", clean_json.strip()).strip()
            data = json.loads(clean_json)
            return data
        except Exception as e:
            logger.warning(f"LLM Classification fallback used: {e}")
            return {}

    def process_document_metadata(
        self,
        text: str,
        document_id: str,
        source_file: str,
        total_pages: int = 1,
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> LandDocumentMetadata:
        user_overrides = user_overrides or {}

        # 1. Deterministic Extraction (High Precision & Priority)
        det_meta = self.extract_deterministic_metadata(text)

        # 2. LLM Extraction (Secondary Fallback)
        llm_meta = self.classify_and_extract_llm(text[:3000])

        # 3. Merging Logic with Strict Deterministic & User Priority
        category = user_overrides.get("document_category")
        if not category:
            category = det_meta.get("document_category_hint") or llm_meta.get("document_category") or "Land Record / Revenue Record"

        valid_categories = [e.value for e in DocumentCategoryEnum]
        if category not in valid_categories:
            category = "Land Record / Revenue Record"

        merged_payload = {
            "document_id": document_id,
            "source_file": source_file,
            "document_category": category,
            "language": llm_meta.get("language") or "English",
            "total_pages": total_pages,

            # User Overrides > Deterministic Regex > LLM Fallback
            "project_id": user_overrides.get("project_id") or det_meta.get("project_id") or llm_meta.get("project_id"),
            "state": user_overrides.get("state") or det_meta.get("state"),
            "district": user_overrides.get("district") or det_meta.get("district"),
            "tehsil": user_overrides.get("tehsil") or det_meta.get("tehsil"),
            "village": user_overrides.get("village") or det_meta.get("village"),
            "survey_number": user_overrides.get("survey_number") or det_meta.get("survey_number"),
            "survey_numbers": det_meta.get("survey_numbers", []),
            "acquisition_stage": det_meta.get("acquisition_stage"),
            "document_date": det_meta.get("document_date"),
            "authority": llm_meta.get("authority")
        }

        # 4. Strict Pydantic Validation & Normalization
        verified_metadata = LandDocumentMetadata(**merged_payload)
        return verified_metadata
