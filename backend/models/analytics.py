from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class OperationEnum(str, Enum):
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    GROUP_BY = "GROUP_BY"
    LIST = "LIST"


class MetricFieldEnum(str, Enum):
    PARCEL_ID = "parcel_id"
    TOTAL_AWARD_AMOUNT = "total_award_amount"
    AREA_HECTARES = "area_hectares"
    CASE_ID = "case_id"


class GroupByFieldEnum(str, Enum):
    VILLAGE = "village"
    DISTRICT = "district"
    ACQUISITION_STATUS = "acquisition_status"
    PAYMENT_STATUS = "payment_status"
    LAND_CATEGORY = "land_category"


class AnalyticsFilter(BaseModel):
    project_id: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    acquisition_status: Optional[str] = None
    payment_status: Optional[str] = None
    land_category: Optional[str] = None
    survey_number: Optional[str] = None
    parcel_id: Optional[str] = None


class AnalyticsRequest(BaseModel):
    query: str = Field(..., description="Original user natural language query")
    operation: str = Field(default="COUNT", description="Allowed operation: COUNT, SUM, AVG, GROUP_BY, LIST")
    target_entity: str = Field(default="parcels", description="Target table/entity: parcels, compensation_awards, acquisition_cases")
    metric_field: Optional[str] = Field(default="parcel_id", description="Field to aggregate: parcel_id, total_award_amount, area_hectares")
    group_by_field: Optional[str] = Field(default=None, description="Field to group by: village, district, acquisition_status, payment_status, land_category")
    filters: AnalyticsFilter = Field(default_factory=AnalyticsFilter, description="Structured filters applied to dataset")
    project_id: Optional[str] = Field(default=None, description="Optional scoped project identifier")
    is_ambiguous: bool = Field(default=False, description="True if query intent cannot be mapped deterministically")
    is_unsupported: bool = Field(default=False, description="True if request falls outside supported analytics operations")
    rejection_reason: Optional[str] = Field(default=None, description="Human-readable reason if query was rejected")


class AnalyticsResultRow(BaseModel):
    group_key: Optional[str] = None
    metric_value: Optional[float] = None
    count: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class AnalyticsResult(BaseModel):
    operation: str
    target_entity: str = "parcels"
    metric_field: Optional[str] = None
    group_by_field: Optional[str] = None
    aggregate_value: Optional[float] = None
    row_count: int = 0
    rows: List[Dict[str, Any]] = []
    applied_filters: Dict[str, Any] = {}
    execution_source: str = "Authoritative PostgreSQL Database"


class AnalyticsResponse(BaseModel):
    query: str
    parsed_request: Optional[AnalyticsRequest] = None
    result: AnalyticsResult
    summary_explanation: str
    source: str = "Authoritative PostgreSQL Database"
    is_valid_analytical_query: bool = True
    error_message: Optional[str] = None
