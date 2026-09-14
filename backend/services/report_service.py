import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.models.report import (
    ProjectReportRequest,
    ProjectReportResponse,
    ReportSection,
    ReportCitation,
    ReportConflict
)
from backend.services.db_service import DatabaseService
from backend.services.retrieval_service import RetrievalService
from backend.models.retrieval import RetrievalRequest
from backend.services.conflict_detector import ConflictDetector
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ReportService:
    """
    Generates structured AI MIS Land Acquisition Project Reports.
    Calculates all numerical statistics deterministically from PostgreSQL before invoking LLM for grounded formatting.
    """

    def __init__(
        self,
        db_service: DatabaseService,
        retrieval_service: RetrievalService,
        conflict_detector: ConflictDetector,
        llm_service: LLMService
    ):
        self.db_service = db_service
        self.retrieval_service = retrieval_service
        self.conflict_detector = conflict_detector
        self.llm_service = llm_service

    def generate_project_report(self, project_id: str) -> ProjectReportResponse:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Retrieve Authoritative Parcel Facts from PostgreSQL / In-Memory Store
        parcels = self.db_service.get_authoritative_project_parcels(project_id)

        # 2. Compute Deterministic Statistical Aggregation in Python
        total_parcels = len(parcels)
        total_area = sum(p.get("area_hectares") or 0.0 for p in parcels)
        total_compensation = sum(p.get("total_award_amount") or 0.0 for p in parcels)

        stage_counts: Dict[str, int] = {}
        payment_counts: Dict[str, int] = {}
        village_counts: Dict[str, Dict[str, Any]] = {}
        land_cat_counts: Dict[str, int] = {}

        for p in parcels:
            stg = p.get("acquisition_status") or "Pending Notification"
            stage_counts[stg] = stage_counts.get(stg, 0) + 1

            pmt = p.get("payment_status") or "Pending"
            payment_counts[pmt] = payment_counts.get(pmt, 0) + 1

            vil = p.get("village") or "Unknown"
            if vil not in village_counts:
                village_counts[vil] = {"parcel_count": 0, "total_award": 0.0}
            village_counts[vil]["parcel_count"] += 1
            village_counts[vil]["total_award"] += (p.get("total_award_amount") or 0.0)

            cat = p.get("land_category") or "Agricultural"
            land_cat_counts[cat] = land_cat_counts.get(cat, 0) + 1

        structured_metrics = {
            "project_id": project_id,
            "total_parcels": total_parcels,
            "total_area_hectares": round(total_area, 4),
            "total_awarded_compensation": round(total_compensation, 2),
            "acquisition_stage_breakdown": stage_counts,
            "payment_status_breakdown": payment_counts,
            "village_distribution": village_counts,
            "land_category_distribution": land_cat_counts
        }

        # 3. Retrieve Grounded RAG Document Evidence for Project
        retrieval_req = RetrievalRequest(
            query=f"Land acquisition project notification award compensation status for {project_id}",
            top_k=10,
            filters_override={"project_id": project_id}
        )
        ret_response = self.retrieval_service.retrieve(retrieval_req)
        evidence_list = ret_response.evidence or []

        # 4. Extract Page-Level Citations
        citations: List[ReportCitation] = []
        seen_citations = set()
        for ev in evidence_list:
            cit_key = (ev.document_id, ev.file_name, ev.page_number)
            if cit_key not in seen_citations:
                citations.append(ReportCitation(
                    document_id=ev.document_id,
                    file_name=ev.file_name,
                    page_number=ev.page_number,
                    excerpt=ev.excerpt[:150] + "..." if len(ev.excerpt) > 150 else ev.excerpt
                ))
                seen_citations.add(cit_key)

        # 5. Deterministic Conflict Detection
        raw_conflicts = self.conflict_detector.detect_conflicts(parcels, evidence_list)
        conflicts: List[ReportConflict] = []
        for c in raw_conflicts:
            conflicts.append(ReportConflict(
                field_name=c.field_name,
                authoritative_value=c.authoritative_value,
                document_value=c.document_value,
                document_id=c.document_id,
                file_name=c.file_name,
                page_number=c.page_number,
                conflict_type=c.conflict_type
            ))

        # 6. Determine Evidence Coverage
        if evidence_list:
            coverage = "COMPLETE" if len(evidence_list) >= 2 else "PARTIAL"
        else:
            coverage = "INSUFFICIENT"

        # 7. LLM Grounded Summarization & Report Formatting
        sections, exec_summary, full_md = self._build_report_content(
            project_id=project_id,
            metrics=structured_metrics,
            citations=citations,
            conflicts=conflicts,
            evidence_list=evidence_list,
            coverage=coverage,
            generated_at=now_str
        )

        return ProjectReportResponse(
            project_id=project_id,
            report_title=f"Land Acquisition MIS Status Report — {project_id}",
            generated_at=now_str,
            executive_summary=exec_summary,
            sections=sections,
            citations=citations,
            conflicts=conflicts,
            evidence_coverage=coverage,
            source="Authoritative PostgreSQL Database + Grounded RAG Documents",
            structured_metrics=structured_metrics,
            markdown_content=full_md
        )

    def _build_report_content(
        self,
        project_id: str,
        metrics: Dict[str, Any],
        citations: List[ReportCitation],
        conflicts: List[ReportConflict],
        evidence_list: List[Any],
        coverage: str,
        generated_at: str
    ) -> tuple:
        # Construct grounded context for LLM formatting
        ev_summary = "\n".join([
            f"- [{ev.file_name}, Page {ev.page_number}]: \"{ev.excerpt[:200]}\""
            for ev in evidence_list[:5]
        ]) if evidence_list else "No document evidence chunks found."

        conf_summary = "\n".join([
            f"- Discrepancy in {c.field_name}: Database={c.authoritative_value} vs Document={c.document_value} (Source: {c.file_name}, p.{c.page_number})"
            for c in conflicts
        ]) if conflicts else "No inconsistencies detected."

        prompt = f"""
You are a specialized Land Acquisition MIS Report Writer.
Generate a structured, professional Land Acquisition Status Report strictly grounded in the provided facts below.

RULES:
1. Preserve exact numerical database metrics. DO NOT recalculate or invent any numbers.
2. If evidence for R&R or Possession is missing, explicitly state: "Information not available in current records."
3. DO NOT produce future delay predictions, delay probability scores, or expected delay days.
4. DO NOT make unsupported legal conclusions.
5. Ground document statements using page-level citations.

DETERMINISTIC DATABASE METRICS:
- Project ID: {project_id}
- Total Parcels: {metrics['total_parcels']}
- Total Area: {metrics['total_area_hectares']} Hectares
- Total Compensation Awarded: ₹{metrics['total_awarded_compensation']:,.2f}
- Acquisition Stages: {metrics['acquisition_stage_breakdown']}
- Payment Statuses: {metrics['payment_status_breakdown']}
- Village Distribution: {metrics['village_distribution']}

DOCUMENT EVIDENCE:
{ev_summary}

DATA QUALITY & CONFLICTS:
{conf_summary}

FORMAT INSTRUCTION:
Write a comprehensive report in GitHub Markdown with these exact section headings:
## Executive Summary
## Acquisition Progress
## Compensation Status
## Rehabilitation & Resettlement (R&R)
## Possession Status
## Document Evidence
## Data Quality & Conflicts
## Overall Status Summary
"""

        try:
            llm_text = self.llm_service.generate_response(prompt)
        except Exception as e:
            logger.error(f"Error calling LLM for report formatting: {e}")
            llm_text = self._fallback_report_text(project_id, metrics, conflicts, coverage)

        # Parse sections from generated markdown text
        sections = []
        exec_summary = f"Project report for {project_id} covering {metrics['total_parcels']} parcels with total awarded compensation of ₹{metrics['total_awarded_compensation']:,.2f}."

        section_titles = [
            "Executive Summary",
            "Acquisition Progress",
            "Compensation Status",
            "Rehabilitation & Resettlement (R&R)",
            "Possession Status",
            "Document Evidence",
            "Data Quality & Conflicts",
            "Overall Status Summary"
        ]

        for title in section_titles:
            pattern = rf"##\s*{re.escape(title)}\s*\n(.*?)(?=\n##|\Z)"
            match = re.search(pattern, llm_text, re.DOTALL | re.IGNORECASE)
            content = match.group(1).strip() if match else "Information not available in current records."
            if title == "Executive Summary" and match:
                exec_summary = content
            sections.append(ReportSection(section_title=title, content=content))

        # Build full markdown document
        md_lines = [
            f"# 🗺️ Land Acquisition MIS Status Report: {project_id}",
            f"**Generated at:** `{generated_at}` | **Evidence Coverage:** `{coverage}`",
            f"**Source:** `Authoritative PostgreSQL Database + Grounded RAG Documents`",
            "\n---\n"
        ]
        for sec in sections:
            md_lines.append(f"## {sec.section_title}\n{sec.content}\n")

        if citations:
            md_lines.append("## 📚 Document Source Citations")
            for cit in citations:
                md_lines.append(f"- 📌 **[Source: {cit.file_name}, p.{cit.page_number}]** (`{cit.document_id}`)")

        if conflicts:
            md_lines.append("\n## ⚠️ Detected Discrepancies")
            for c in conflicts:
                md_lines.append(
                    f"- **{c.conflict_type}** for `{c.field_name}`: Database Fact=`{c.authoritative_value}` vs Document=`{c.document_value}` (Source: `{c.file_name}`, p.{c.page_number})"
                )

        full_md = "\n".join(md_lines)
        return sections, exec_summary, full_md

    def _fallback_report_text(self, project_id: str, metrics: Dict[str, Any], conflicts: List[ReportConflict], coverage: str) -> str:
        return f"""
## Executive Summary
Project status report for {project_id}. Total recorded area is {metrics['total_area_hectares']} Ha across {metrics['total_parcels']} parcel(s). Total awarded compensation is ₹{metrics['total_awarded_compensation']:,.2f}.

## Acquisition Progress
Stage distribution: {metrics['acquisition_stage_breakdown']}.

## Compensation Status
Payment distribution: {metrics['payment_status_breakdown']}. Total compensation: ₹{metrics['total_awarded_compensation']:,.2f}.

## Rehabilitation & Resettlement (R&R)
Information not available in current records.

## Possession Status
Information not available in current records.

## Document Evidence
Retrieved document evidence coverage: {coverage}.

## Data Quality & Conflicts
{'Discrepancies found: ' + str(len(conflicts)) if conflicts else 'No inconsistencies detected.'}

## Overall Status Summary
Active land acquisition project in progress.
"""
