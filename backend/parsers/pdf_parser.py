import fitz
from ..core.ocr import OCRService
from pdf2image import convert_from_path

def parse_pdf(file_path: str, ocr_service: OCRService) -> str:
    pages_text = []

    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document):
            page_text = page.get_text("text")
            if not page_text.strip():
                image = convert_from_path(file_path,
                                           first_page = page_number+1,
                                           last_page = page_number+1)[0]
                page_text = ocr_service.extract_text(image)
            pages_text.append(f"--- PAGE {page_number + 1} ---\n{page_text}")

    return "\n".join(pages_text)

