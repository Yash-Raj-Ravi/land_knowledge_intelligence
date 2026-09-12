from typing import List, Optional
from pydantic import BaseModel
from backend.models.search import SearchResult
from backend.models.retrieval import RetrievalResponse
from backend.services.conflict_detector import ConflictItem

class CitationItem(BaseModel):
    document_id: str
    file_name: str
    page_number: int

class AskRequest(BaseModel):
    query: str
    top_k: int = 10
    project_id: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    citations: List[CitationItem] = []
    evidence_coverage: str = "INSUFFICIENT" # COMPLETE | PARTIAL | INSUFFICIENT
    conflicts: List[ConflictItem] = []
    retrieval_response: Optional[RetrievalResponse] = None

# Backward compatibility wrappers
class RAGRequest(BaseModel):
    query: str
    top_k: int = 10
    include_sources: bool = True

class RAGResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None
    sources: Optional[List[SearchResult]] = None
    citations: Optional[List[CitationItem]] = None
    evidence_coverage: Optional[str] = None


