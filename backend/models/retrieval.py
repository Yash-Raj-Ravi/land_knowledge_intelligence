from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class QueryFilter(BaseModel):
    project_id: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    tehsil: Optional[str] = None
    village: Optional[str] = None
    raw_survey_number: Optional[str] = None
    normalized_survey_number: Optional[str] = None
    survey_number: Optional[str] = None
    parcel_id: Optional[str] = None
    document_category: Optional[str] = None
    acquisition_stage: Optional[str] = None
    document_date: Optional[str] = None
    has_reliable_filter: bool = False

class EvidenceSource(BaseModel):
    document_id: str
    file_name: str
    page_number: int
    section_heading: str
    chunk_id: int
    raw_survey_number: Optional[str] = None
    survey_number: Optional[str] = None
    project_id: Optional[str] = None
    excerpt: str
    distance: float = 0.0
    distance_metric: str = "l2"

class RetrievalRequest(BaseModel):
    query: str = Field(..., description="User natural language question")
    top_k: int = Field(default=10, description="Max candidate vector chunks to retrieve")
    filters_override: Optional[Dict[str, Any]] = Field(default=None, description="Optional explicit UI filter overrides")

class RetrievalResponse(BaseModel):
    query: str
    parsed_filters: Dict[str, Any] = Field(default_factory=dict, description="Deterministic filters parsed from user query")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="Filters actually applied to vector search & PG")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Combined effective filters")
    structured_records: List[Dict[str, Any]] = Field(default_factory=list, description="Authoritative PostgreSQL parcel/financial records")
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Ranked ChromaDB text chunks")
    evidence: List[EvidenceSource] = Field(default_factory=list, description="Standard Evidence Citation Objects")
    candidate_count: int = 0
    retrieved_count: int = 0
    ranking_method: str = "Deterministic (Exact Survey > Exact Project > Category/Stage > Similarity > Diversity)"
    distance_metric: str = "l2"
    supporting_source_count: int = 0
    evidence_coverage: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT"] = "INSUFFICIENT"
    reliable_filter_found: bool = True

