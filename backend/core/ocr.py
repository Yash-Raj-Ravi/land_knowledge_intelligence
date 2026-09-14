import logging
from pathlib import Path
from PIL import Image
import pytesseract
from backend.config import TESSERACT_PATH

logger = logging.getLogger(__name__)


class OCRService:
    """
    Language-aware OCR Service using Tesseract.
    Supports English (eng), Hindi (hin), and Marathi (mar).
    Detects installed language packs and falls back gracefully with clear warnings if missing.
    """

    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)
        self.available_languages = self.detect_installed_languages()

    def detect_installed_languages(self) -> list:
        try:
            langs = pytesseract.get_languages(config="")
            logger.info(f"Tesseract OCR installed languages: {langs}")
            return langs
        except Exception as e:
            logger.warning(f"Could not query Tesseract installed languages: {e}")
            return ["eng"]

    def resolve_ocr_lang(self, requested_lang: str = "eng") -> str:
        """
        Constructs valid Tesseract lang parameter based on requested language and installed langpacks.
        Constraint: Prefers language-specific OCR; falls back to available language packs if missing.
        """
        if not requested_lang:
            requested_lang = "eng"

        requested_tokens = [t.strip() for t in requested_lang.split("+") if t.strip()]
        available_set = set(self.available_languages)

        valid_tokens = [t for t in requested_tokens if t in available_set]
        missing_tokens = [t for t in requested_tokens if t not in available_set]

        if missing_tokens:
            tessdata_dir = Path(TESSERACT_PATH).parent / "tessdata"
            logger.warning(
                f"Missing Tesseract OCR language data pack(s): {missing_tokens}. "
                f"To enable full Hindi/Marathi OCR, place 'hin.traineddata' and 'mar.traineddata' "
                f"in: {tessdata_dir}"
            )

        if valid_tokens:
            return "+".join(valid_tokens)
        elif "eng" in available_set:
            return "eng"
        elif self.available_languages:
            return self.available_languages[0]
        else:
            return "eng"

    def extract_text(self, image: Image.Image, lang: str = "eng") -> str:
        ocr_lang = self.resolve_ocr_lang(lang)
        try:
            return pytesseract.image_to_string(image, lang=ocr_lang)
        except Exception as e:
            logger.error(f"OCR execution failed with lang='{ocr_lang}': {e}")
            if ocr_lang != "eng":
                try:
                    return pytesseract.image_to_string(image, lang="eng")
                except Exception:
                    pass
            return ""