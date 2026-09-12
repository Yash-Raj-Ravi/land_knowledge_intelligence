from ..services.document_service import DocumentService
from ..services.chunk_service import ChunkService
from ..services.embedding_service import EmbeddingService
from ..services.search_service import SearchService
from ..services.rag_service import RAGService
from ..services.repository_service import RepositoryService
from ..vectorstore.chroma_store import ChromaStore
from ..embedding.embedding_model import EmbeddingModel
from ..services.llm_service import LLMService
from ..services.entity_service import EntityService
from ..services.db_service import DatabaseService
from ..services.classification_service import ClassificationService
from ..services.query_parser import QueryParser
from ..services.retrieval_service import RetrievalService
from ..llm.llm_model import LLMModel
from ..core.ocr import OCRService
from fastapi import Depends

# leading underscore is used to indicate these are private module-level instances:

_store = ChromaStore()
_embedding_model = EmbeddingModel()
_embedding_service = EmbeddingService(_embedding_model)
_search_service = SearchService(
    _embedding_service,
    _store,
)
_llm_model = LLMModel()
_llm_service = LLMService(_llm_model)
_entity_service = EntityService(_llm_model)
_db_service = DatabaseService()
_classification_service = ClassificationService(_llm_model)
_query_parser = QueryParser(_llm_model)
_retrieval_service = RetrievalService(
    query_parser=_query_parser,
    embedding_service=_embedding_service,
    db_service=_db_service,
    store=_store
)

from ..services.conflict_detector import ConflictDetector
from ..services.context_builder import ContextBuilder

_conflict_detector = ConflictDetector()
_context_builder = ContextBuilder()

_ocr_service = OCRService()
_document_service = DocumentService(_ocr_service)
_chunk_service = ChunkService(_document_service)

_rag_service = RAGService(
    retrieval_service=_retrieval_service,
    conflict_detector=_conflict_detector,
    context_builder=_context_builder,
    llm_service=_llm_service,
)


def get_document_service():
    return _document_service

def get_chunk_service():
    return _chunk_service

def get_embedding_service():
    return _embedding_service

def get_rag_service():
    return _rag_service

def get_search_service():
    return _search_service

def get_chroma_store():
    return _store

def get_ocr_service():
    return _ocr_service

def get_repository_service(
    store: ChromaStore = Depends(get_chroma_store)
):
    return RepositoryService(store)

def get_entity_service():
    return _entity_service

def get_db_service():
    return _db_service

def get_classification_service():
    return _classification_service

def get_query_parser():
    return _query_parser

def get_retrieval_service():
    return _retrieval_service

def get_conflict_detector():
    return _conflict_detector

def get_context_builder():
    return _context_builder

def get_llm_service():
    return _llm_service

