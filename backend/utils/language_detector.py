import re
from typing import Dict, Any

# Keyword sets for language classification heuristics
MARATHI_KEYWORDS = {
    "आहे", "सर्व्हे", "गट", "माहिती", "जिल्हा", "तालुका", "शासकीय", "ग्रामपंचायत",
    "सातबारा", "हक्क", "अर्जातील", "गाव", "क्षेत्रफळ", "खातेदार", "बाधित", "निवाडा"
}

HINDI_KEYWORDS = {
    "है", "अनुभाग", "परियोजना", "विवरण", "संख्या", "जिला", "तहसील", "खसरा",
    "मुआवजा", "अधिसूचना", "ग्राम", "एवम्", "स्वीकृति", "अर्जन", "क्षेत्रफल"
}

ENGLISH_KEYWORDS = {
    "survey", "parcel", "award", "compensation", "notification", "district",
    "village", "tehsil", "acquisition", "land", "section", "possession"
}


def detect_language(text: str) -> Dict[str, Any]:
    """
    Lightweight heuristic language detector.
    Returns:
        {
            "language": "en" | "hi" | "mr" | "unknown",
            "confidence": float (0.0 to 1.0)
        }
    Constraint: Low-confidence detection (< 0.5) returns "unknown".
    """
    if not text or not isinstance(text, str) or not text.strip():
        return {"language": "unknown", "confidence": 0.0}

    text_clean = text.strip()

    # 1. Count Devanagari script characters vs Latin ASCII characters
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text_clean))
    latin_chars = len(re.findall(r"[A-Za-z]", text_clean))
    total_chars = devanagari_chars + latin_chars

    if total_chars == 0:
        return {"language": "unknown", "confidence": 0.0}

    devanagari_ratio = devanagari_chars / total_chars

    # 2. Devanagari Script Dominant (Hindi or Marathi)
    if devanagari_ratio > 0.4:
        words = set(re.findall(r"[\u0900-\u097F]+", text_clean))

        marathi_hits = len(words.intersection(MARATHI_KEYWORDS))
        hindi_hits = len(words.intersection(HINDI_KEYWORDS))

        if marathi_hits > hindi_hits:
            confidence = min(0.6 + (marathi_hits * 0.1), 0.98)
            return {"language": "mr", "confidence": round(confidence, 2)}
        elif hindi_hits > marathi_hits:
            confidence = min(0.6 + (hindi_hits * 0.1), 0.98)
            return {"language": "hi", "confidence": round(confidence, 2)}
        else:
            # High Devanagari ratio, but keyword match tie
            return {"language": "hi", "confidence": round(min(devanagari_ratio, 0.75), 2)}

    # 3. Latin Script Dominant (English)
    elif latin_chars / max(total_chars, 1) > 0.6:
        words_lower = set(re.findall(r"[a-z]+", text_clean.lower()))
        eng_hits = len(words_lower.intersection(ENGLISH_KEYWORDS))
        confidence = min(0.7 + (eng_hits * 0.05), 0.99)
        return {"language": "en", "confidence": round(confidence, 2)}

    # Low-confidence fallback
    return {"language": "unknown", "confidence": 0.3}
