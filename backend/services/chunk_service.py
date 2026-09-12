from backend.services.document_service import DocumentService
from backend.chunking.structure_chunker import StructureChunker
from backend.config import CHUNK_TARGET_MIN, CHUNK_TARGET_MAX, MAX_TABLE_ROWS_PER_CHUNK
from backend.models.land_metadata import LandDocumentMetadata

class ChunkService:

    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
        self.chunker = StructureChunker(
            target_min=CHUNK_TARGET_MIN,
            target_max=CHUNK_TARGET_MAX,
            max_table_rows=MAX_TABLE_ROWS_PER_CHUNK
        )

    def chunk_document(self, file_path: str, doc_metadata: LandDocumentMetadata) -> list[dict]:
        text = self.document_service.parse_document(file_path)
        chunks = self.chunker.chunk_document_text(text, doc_metadata)
        return chunks







