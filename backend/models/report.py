from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProjectReportRequest(BaseModel):
    project_id: str = Field(..., description="Project Identifier for report generation (e.g. PRJ-NHAI-2024)")


class ReportSection(BaseModel):
    section_title: str
    content: str
    key_metrics: Optional[Dict[str, Any]] = None


class ReportCitation(BaseModel):
    document_id: str
    file_name: str
    page_number: int
    excerpt: Optional[str] = None


class ReportConflict(BaseModel):
    field_name: str
    authoritative_value: str
    document_value: str
    document_id: str
    file_name: str
    page_number: int
    conflict_type: str = "Numerical Discrepancy"


class ProjectReportResponse(BaseModel):
    project_id: str
    report_title: str
    generated_at: str
    executive_summary: str
    sections: List[ReportSection] = Field(default_factory=list)
    citations: List[ReportCitation] = Field(default_factory=list)
    conflicts: List[ReportConflict] = Field(default_factory=list)
    evidence_coverage: str = "INSUFFICIENT" # COMPLETE | PARTIAL | INSUFFICIENT
    source: str = "Authoritative PostgreSQL Database + Grounded RAG Documents"
    structured_metrics: Dict[str, Any] = Field(default_factory=dict)
    markdown_content: str = ""
