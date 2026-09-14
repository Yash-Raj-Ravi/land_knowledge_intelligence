from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import re

class DocumentCategoryEnum(str, Enum):
    LAND_RECORD = "Land Record / Revenue Record"
    NOTIFICATION = "Acquisition Notification"
    AWARD = "Award"
    COMPENSATION = "Compensation Record"
    RR_RECORD = "R&R Record"
    POSSESSION = "Possession Record"
    GOVT_ORDER = "Government Order / Approval"
    SURVEY_REPORT = "Survey / Inspection Report"
    LEGAL_DISPUTE = "Legal / Dispute Document"

class LandEmbedRequest(BaseModel):
    file_path: str
    project_id: Optional[str] = None
    document_category: Optional[str] = None
    village: Optional[str] = None
    survey_number: Optional[str] = None

INVALID_SURVEY_TOKENS = {"NO", "SURVEY", "PLOT", "GAT", "KHASRA", "THE", "PAGE", "AND", "OF", "NIL", "NONE"}

def sanitize_survey_number(val: str) -> Optional[str]:
    if not val:
        return None
    val_clean = val.strip().strip(".,;:()")
    val_upper = val_clean.upper()
    if val_upper in INVALID_SURVEY_TOKENS or len(val_clean) < 1 or len(val_clean) > 25:
        return None
    if val_clean.isdigit() and len(val_clean) > 6:
        return None # Rejected if random long integer
    return val_clean

class LandDocumentMetadata(BaseModel):
    # Required Fields
    document_id: str = Field(..., description="Unique UUID for document")
    source_file: str = Field(..., description="Original filename")
    document_category: str = Field(..., description="1 of 9 document categories")
    language: str = Field(default="English", description="Document primary language")
    total_pages: int = Field(default=1, description="Total page count")
    
    # Optional Fields (Extracted / Provided)
    project_id: Optional[str] = Field(default=None, description="Land Acquisition Project Identifier")
    state: Optional[str] = Field(default=None, description="State name")
    district: Optional[str] = Field(default=None, description="District name")
    tehsil: Optional[str] = Field(default=None, description="Tehsil / Taluka name")
    village: Optional[str] = Field(default=None, description="Revenue Village / Mauza name")
    survey_number: Optional[str] = Field(default=None, description="Primary survey / Plot / Khasra number")
    survey_numbers: List[str] = Field(default_factory=list, description="List of all survey numbers in document")
    parcel_id: Optional[str] = Field(default=None, description="Unique parcel identifier")
    acquisition_stage: Optional[str] = Field(default=None, description="Statutory stage (e.g. Section 19)")
    document_date: Optional[str] = Field(default=None, description="Document issue date (YYYY-MM-DD)")
    authority: Optional[str] = Field(default=None, description="Issuing authority (e.g. SLAO)")

    @field_validator("project_id", mode="before")
    def validate_project_id(cls, v):
        if not v or not isinstance(v, str):
            return None
        v_clean = v.strip().upper()
        if len(v_clean) < 2 or len(v_clean) > 50:
            return None
        return v_clean

    @field_validator("state", "district", "tehsil", "village", mode="before")
    def validate_name_fields(cls, v):
        if not v or not isinstance(v, str):
            return None
        v_clean = v.strip().title()
        if len(v_clean) < 2 or len(v_clean) > 60:
            return None
        return v_clean

    @field_validator("survey_number", mode="before")
    def validate_single_survey(cls, v):
        if not v or not isinstance(v, str):
            return None
        return sanitize_survey_number(v)

    @field_validator("survey_numbers", mode="before")
    def validate_survey_list(cls, v):
        if not v:
            return []
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",") if s.strip()]
        cleaned = []
        for item in v:
            san = sanitize_survey_number(str(item))
            if san and san not in cleaned:
                cleaned.append(san)
        return cleaned

class LandChunkMetadata(BaseModel):
    document_id: str
    source_file: str
    document_category: str
    page_number: int
    chunk_id: int
    chunk_type: str = "prose" # prose, legal_clause, table_schedule
    section_heading: Optional[str] = None
    survey_numbers: List[str] = Field(default_factory=list)
    
    # Inherited Optional Fields for filtering
    project_id: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    tehsil: Optional[str] = None
    village: Optional[str] = None
    parcel_id: Optional[str] = None
    acquisition_stage: Optional[str] = None
    document_date: Optional[str] = None
    authority: Optional[str] = None
    language: str = "English"
