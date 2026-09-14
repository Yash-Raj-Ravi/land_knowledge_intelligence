import re
from typing import Dict, Any, Optional

TERMINOLOGY_MAPPINGS = {
    # Village
    "मौजे": "village",
    "गाव": "village",
    "गाँव": "village",
    "गांव": "village",
    "ग्राम": "village",

    # Tehsil / Taluka
    "तालुका": "tehsil",
    "तहसील": "tehsil",

    # District
    "जिल्हा": "district",
    "जिला": "district",

    # State
    "राज्य": "state",

    # Project
    "प्रकल्प": "project",
    "परियोजना": "project",

    # Survey Number
    "सर्व्हे नंबर": "survey_number",
    "सर्व्हे क्र": "survey_number",
    "सर्व्हे क्रमांक": "survey_number",
    "गट क्र": "survey_number",
    "गट क्रमांक": "survey_number",
    "खसरा नं": "survey_number",
    "खसरा नंबर": "survey_number",

    # Compensation
    "मोबदला": "compensation",
    "मुआवजा": "compensation",
    "क्षतिपूर्ति": "compensation",

    # Possession
    "ताबा": "possession",
    "कब्जा": "possession",

    # R&R
    "पुनर्वसन": "rehabilitation"
}


class MultilingualService:
    """
    Multilingual Domain Terminology Normalizer.
    Maps Hindi and Marathi land acquisition terms to canonical concepts
    without altering or destroying the original source-language text or survey identifiers.
    """

    def normalize_term(self, term: str) -> Optional[str]:
        if not term or not isinstance(term, str):
            return None
        term_clean = term.strip().lower()
        return TERMINOLOGY_MAPPINGS.get(term_clean)

    def extract_canonical_concepts(self, text: str) -> Dict[str, Any]:
        """
        Extracts canonical concepts found in Devanagari text.
        Returns a dict of extracted canonical metadata fields.
        Does NOT alter or destroy raw text.
        """
        extracted = {}
        if not text:
            return extracted

        # Check for terminology mappings
        for key, canonical_concept in TERMINOLOGY_MAPPINGS.items():
            if key in text:
                extracted[canonical_concept] = extracted.get(canonical_concept, True)

        return extracted

    def get_canonical_query_filters(self, query: str) -> Dict[str, Any]:
        """
        Translates regional query keywords into canonical metadata query filter keys.
        """
        filters = {}
        q_lower = query.strip()

        for regional_term, canonical in TERMINOLOGY_MAPPINGS.items():
            if regional_term in q_lower:
                filters[f"has_{canonical}"] = True

        return filters
