import re
from typing import List, Dict, Any, Optional
from backend.models.chunk import Chunk
from backend.models.land_metadata import LandChunkMetadata, LandDocumentMetadata, sanitize_survey_number

class StructureChunker:
    def __init__(self, target_min: int = 800, target_max: int = 1200, max_table_rows: int = 10):
        self.target_min = target_min
        self.target_max = target_max
        self.max_table_rows = max_table_rows

    def extract_survey_numbers_from_text(self, text: str) -> List[str]:
        patterns = [
            r"(?:Survey|S\.?\s*No\.?|Gat\s*No\.?|Khasra\s*No\.?|Plot\s*No\.?)\s*:?\s*([A-Za-z0-9\/\-]+)",
            r"(?:Gat|Khasra|Survey)\s+([0-9]+\/[0-9]+[A-Za-z]?|[0-9]+)",
            r"\b([0-9]{1,4}\/[0-9]{1,3}[A-Za-z]{0,2})\b" # Matches 142/3A, 145/1, etc.
        ]
        found = set()
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                clean_m = sanitize_survey_number(m)
                if clean_m:
                    found.add(clean_m)
        return sorted(list(found))


    def is_table_row(self, line: str) -> bool:
        # Tables often contain multiple commas, pipes, or tab separations
        separators = line.count(",") + line.count("|") + line.count("\t")
        return separators >= 2 or bool(re.search(r"\b\d+\s*/\s*\d+\b", line))

    def is_heading(self, line: str) -> bool:
        line_clean = line.strip()
        if not line_clean:
            return False
        if line_clean.isupper() and len(line_clean) < 100:
            return True
        if re.match(r"^(?:Section|Chapter|SCHEDULE|PART|ANNEXURE|\d+\.)\s+", line_clean, re.IGNORECASE):
            return True
        return False

    def chunk_document_text(
        self,
        full_text: str,
        doc_metadata: LandDocumentMetadata
    ) -> List[Dict[str, Any]]:
        lines = full_text.split("\n")
        chunks = []

        current_heading = "General Document Text"
        current_buffer = []
        current_char_count = 0
        current_chunk_type = "prose"
        current_table_rows = 0
        current_page = 1
        chunk_counter = 1

        for line in lines:
            # Check page marker (e.g. "--- PAGE 2 ---")
            page_match = re.match(r"^---\s*PAGE\s+(\d+)\s*---$", line.strip(), re.IGNORECASE)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            line_str = line.strip()
            if not line_str:
                continue

            # Update Heading context if detected
            if self.is_heading(line_str):
                # Flush current buffer if substantial
                if current_char_count >= self.target_min:
                    chunk_text = "\n".join(current_buffer)
                    surveys = self.extract_survey_numbers_from_text(chunk_text)
                    chunks.append({
                        "chunk_id": chunk_counter,
                        "text": f"[{doc_metadata.source_file} | Heading: {current_heading}]\n{chunk_text}",
                        "page_number": current_page,
                        "section_heading": current_heading,
                        "chunk_type": current_chunk_type,
                        "survey_numbers": surveys
                    })
                    chunk_counter += 1
                    current_buffer = []
                    current_char_count = 0
                    current_table_rows = 0

                current_heading = line_str
                continue

            # Handle Table Row
            if self.is_table_row(line_str):
                current_chunk_type = "table_schedule"
                current_table_rows += 1

                current_buffer.append(line_str)
                current_char_count += len(line_str)

                # Table row capacity check
                if current_table_rows >= self.max_table_rows or current_char_count >= self.target_max:
                    chunk_text = "\n".join(current_buffer)
                    surveys = self.extract_survey_numbers_from_text(chunk_text)
                    chunks.append({
                        "chunk_id": chunk_counter,
                        "text": f"[{doc_metadata.source_file} | Schedule: {current_heading}]\n{chunk_text}",
                        "page_number": current_page,
                        "section_heading": current_heading,
                        "chunk_type": "table_schedule",
                        "survey_numbers": surveys
                    })
                    chunk_counter += 1
                    current_buffer = []
                    current_char_count = 0
                    current_table_rows = 0
                    current_chunk_type = "prose"
                continue

            # Handle Normal Prose / Clause Line
            if current_chunk_type == "table_schedule":
                # Flush table buffer if switching back to prose
                chunk_text = "\n".join(current_buffer)
                surveys = self.extract_survey_numbers_from_text(chunk_text)
                chunks.append({
                    "chunk_id": chunk_counter,
                    "text": f"[{doc_metadata.source_file} | Schedule: {current_heading}]\n{chunk_text}",
                    "page_number": current_page,
                    "section_heading": current_heading,
                    "chunk_type": "table_schedule",
                    "survey_numbers": surveys
                })
                chunk_counter += 1
                current_buffer = []
                current_char_count = 0
                current_table_rows = 0
                current_chunk_type = "prose"

            current_buffer.append(line_str)
            current_char_count += len(line_str)

            # Check prose buffer threshold
            if current_char_count >= self.target_max:
                chunk_text = "\n".join(current_buffer)
                surveys = self.extract_survey_numbers_from_text(chunk_text)
                chunks.append({
                    "chunk_id": chunk_counter,
                    "text": f"[{doc_metadata.source_file} | Heading: {current_heading}]\n{chunk_text}",
                    "page_number": current_page,
                    "section_heading": current_heading,
                    "chunk_type": "prose",
                    "survey_numbers": surveys
                })
                chunk_counter += 1
                current_buffer = []
                current_char_count = 0

        # Flush remaining buffer
        if current_buffer:
            chunk_text = "\n".join(current_buffer)
            surveys = self.extract_survey_numbers_from_text(chunk_text)
            chunks.append({
                "chunk_id": chunk_counter,
                "text": f"[{doc_metadata.source_file} | Heading: {current_heading}]\n{chunk_text}",
                "page_number": current_page,
                "section_heading": current_heading,
                "chunk_type": current_chunk_type,
                "survey_numbers": surveys
            })

        return chunks
