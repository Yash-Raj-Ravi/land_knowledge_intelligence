from typing import List, Optional
from pydantic import BaseModel, Field


class AnomalyItem(BaseModel):
    parcel_id: str = Field(..., description="Target parcel identifier")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier")
    anomaly_type: str = Field(..., description="Categorical anomaly type (e.g. Area Discrepancy)")
    severity: str = Field(default="medium", description="Severity level: high, medium, low")
    field: str = Field(..., description="Target attribute field (e.g. area_hectares)")
    expected_value: Optional[str] = Field(default=None, description="Expected authoritative value")
    observed_value: Optional[str] = Field(default=None, description="Observed document / ML value")
    source: str = Field(default="Anomaly Detection Service", description="Originating provider / ML model")
    confidence: float = Field(default=0.85, description="Anomaly detection confidence score (0.0 to 1.0)")
    status: str = Field(default="open", description="Anomaly lifecycle status: open, resolved, ignored")


class AnomalyProviderResponse(BaseModel):
    service_status: str = Field(default="online", description="Status of anomaly service: online, unavailable")
    anomalies: List[AnomalyItem] = Field(default_factory=list, description="List of detected parcel anomalies")
    message: Optional[str] = Field(default=None, description="Status or error detail message")
