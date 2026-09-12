import re
import logging
from typing import List, Dict, Any, Optional
from backend.models.land_metadata import sanitize_survey_number

logger = logging.getLogger(__name__)

def parse_area_to_hectares(area_str: str) -> Optional[float]:
    if not area_str:
        return None
    clean = re.sub(r"[^\d\.]", "", area_str.strip())
    try:
        val = float(clean)
        return val if val > 0 else None
    except ValueError:
        return None

def parse_currency_amount(amount_str: str) -> Optional[float]:
    if not amount_str:
        return None
    # Handles Rs, INR, commas, e.g. "INR 24,50,000" or "2450000"
    clean = re.sub(r"[^\d\.]", "", amount_str.strip())
    try:
        val = float(clean)
        return val if val > 0 else None
    except ValueError:
        return None

class TableScheduleExtractor:
    def __init__(self):
        pass

    def extract_structured_parcels(self, full_text: str) -> List[Dict[str, Any]]:
        lines = full_text.split("\n")
        structured_records = []
        current_page = 1

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Track page number
            page_match = re.match(r"^---\s*PAGE\s+(\d+)\s*---$", line_str, re.IGNORECASE)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            # Check if line is table row (contains | or multiple delimiters or plot patterns)
            if "|" in line_str or "," in line_str:
                parts = [p.strip() for p in (line_str.split("|") if "|" in line_str else line_str.split(","))]
                
                # Skip header rows
                joined_row = " ".join(parts).lower()
                if "survey" in joined_row and "category" in joined_row:
                    continue
                if "गट क्रमांक" in joined_row or "क्षेत्रफळ" in joined_row:
                    continue

                if len(parts) >= 3:
                    # Attempt column matching
                    survey_no = None
                    category = None
                    area = None
                    owner = None
                    comp_amount = None

                    for idx, part in enumerate(parts):
                        san_s = sanitize_survey_number(part)
                        if san_s and not survey_no:
                            # Check if valid survey number
                            if re.search(r"\b\d+[\/\-A-Za-z0-9]*\b", san_s):
                                survey_no = san_s
                                continue

                        # Check area column (e.g. 0.4500)
                        if not area:
                            parsed_a = parse_area_to_hectares(part)
                            if parsed_a is not None and parsed_a < 1000:
                                area = parsed_a
                                continue

                        # Check compensation column (e.g. 24,50,000 or 2450000)
                        if not comp_amount:
                            parsed_c = parse_currency_amount(part)
                            if parsed_c is not None and parsed_c >= 1000:
                                comp_amount = parsed_c
                                continue

                        # Check land category
                        part_lower = part.lower()
                        if part_lower in ("agricultural", "commercial", "residential", "forest", "government", "jirayat", "bagayat"):
                            category = part.title()
                            continue

                        # Default text part to owner name if name-like
                        if len(part) >= 3 and not owner and not re.search(r"^\d+$", part):
                            if not any(k in part_lower for k in ["survey", "area", "hectare", "plot", "rs", "inr"]):
                                owner = part.strip()

                    if survey_no:
                        structured_records.append({
                            "survey_number": survey_no,
                            "area_hectares": area,
                            "landowner": owner,
                            "land_category": category or "Agricultural",
                            "compensation_amount": comp_amount,
                            "page_number": current_page
                        })

        return structured_records
