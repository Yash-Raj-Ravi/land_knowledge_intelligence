from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.models.anomaly import AnomalyItem


class ParcelIntelligenceResponse(BaseModel):
    parcel_id: str
    survey_number: str
    village: str
    district: str
    state: str
    project_id: Optional[str] = None
    area_hectares: Optional[float] = None
    land_category: Optional[str] = None
    acquisition_status: Optional[str] = None
    total_award_amount: Optional[float] = None
    payment_status: Optional[str] = None
    landowner: Optional[str] = None
    rr_status: str = "Information not available in current records."
    possession_status: str = "Information not available in current records."
    evidence_count: int = 0
    evidence_summary: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    anomalies: List[AnomalyItem] = Field(default_factory=list)
    anomaly_service_status: str = "online"
    attention_categories: List[str] = Field(default_factory=list)
    source: str = "Authoritative PostgreSQL Database + Grounded RAG Documents"


class ProjectIntelligenceResponse(BaseModel):
    project_id: str
    project_name: str
    state: str
    district: str
    total_parcels: int
    total_area_hectares: float
    total_awarded_compensation: float
    acquisition_stage_counts: Dict[str, int] = Field(default_factory=dict)
    payment_status_counts: Dict[str, int] = Field(default_factory=dict)
    village_counts: Dict[str, int] = Field(default_factory=dict)
    evidence_count: int = 0
    conflict_count: int = 0
    anomaly_count: int = 0
    anomaly_service_status: str = "online"
    report_available: bool = True
    attention_categories: List[str] = Field(default_factory=list)
    source: str = "Authoritative PostgreSQL Database + Grounded RAG Documents"
