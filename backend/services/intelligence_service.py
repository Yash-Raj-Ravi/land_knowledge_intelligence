import logging
from typing import Optional, Dict, Any, List
from backend.models.intelligence import ParcelIntelligenceResponse, ProjectIntelligenceResponse
from backend.services.db_service import DatabaseService
from backend.services.retrieval_service import RetrievalService
from backend.models.retrieval import RetrievalRequest
from backend.services.conflict_detector import ConflictDetector
from backend.services.anomaly_service import AnomalyService
from backend.services.attention_service import AttentionService

logger = logging.getLogger(__name__)


class IntelligenceService:
    """
    Unified AI Integration Service.
    Aggregates authoritative PostgreSQL facts, scoped retrieval evidence, conflict detection,
    fault-tolerant anomaly intelligence, and deterministic current-state attention summaries.
    """

    def __init__(
        self,
        db_service: DatabaseService,
        retrieval_service: RetrievalService,
        conflict_detector: ConflictDetector,
        anomaly_service: AnomalyService,
        attention_service: AttentionService
    ):
        self.db_service = db_service
        self.retrieval_service = retrieval_service
        self.conflict_detector = conflict_detector
        self.anomaly_service = anomaly_service
        self.attention_service = attention_service

    def get_parcel_intelligence(self, parcel_id: str) -> ParcelIntelligenceResponse:
        # Extract survey number from parcel_id if formatted like PCL-VADADALA-142-3A
        survey_number = parcel_id
        village_name = ""
        parts = parcel_id.split("-")
        if len(parts) >= 3:
            village_name = parts[1]
            survey_number = "-".join(parts[2:]).replace("-", "/")

        # 1. Authoritative PostgreSQL Fact Lookup
        parcel_data = self.db_service.get_authoritative_parcel_data(village_name, survey_number)
        if not parcel_data:
            # Fallback search by parcel_id directly
            for p in self.db_service.in_memory_parcels.values():
                if p.get("parcel_id", "").upper() == parcel_id.upper():
                    parcel_data = p
                    break

        if not parcel_data:
            parcel_data = {
                "parcel_id": parcel_id,
                "survey_number": survey_number,
                "village": village_name or "Unknown",
                "district": "Unknown",
                "state": "Unknown"
            }

        # 2. Scoped Document Evidence Retrieval
        ret_req = RetrievalRequest(
            query=f"Parcel {parcel_id} Survey {survey_number} document evidence",
            top_k=5,
            filters_override={"parcel_id": parcel_id}
        )
        ret_resp = self.retrieval_service.retrieve(ret_req)
        evidence_list = ret_resp.evidence or []

        ev_summaries = [
            {
                "document_id": ev.document_id,
                "file_name": ev.file_name,
                "page_number": ev.page_number,
                "excerpt": ev.excerpt[:150]
            }
            for ev in evidence_list
        ]

        # 3. Conflict Detection
        raw_conflicts = self.conflict_detector.detect_conflicts(
            [parcel_data], evidence_list
        )
        conflict_dicts = [c.model_dump() for c in raw_conflicts]

        # 4. Anomaly Intelligence Lookup (Fault Tolerant)
        anomaly_resp = self.anomaly_service.get_anomalies_for_parcel(parcel_id)

        # 5. Deterministic Attention Evaluation (Zero delay prediction)
        attention_flags = self.attention_service.evaluate_parcel_attention(
            parcel_data=parcel_data,
            conflicts=raw_conflicts,
            evidence_list=evidence_list,
            anomalies=anomaly_resp.anomalies
        )

        return ParcelIntelligenceResponse(
            parcel_id=parcel_data.get("parcel_id", parcel_id),
            survey_number=parcel_data.get("survey_number", survey_number),
            village=parcel_data.get("village", "Unknown"),
            district=parcel_data.get("district", "Unknown"),
            state=parcel_data.get("state", "Unknown"),
            project_id=parcel_data.get("project_id"),
            area_hectares=parcel_data.get("area_hectares"),
            land_category=parcel_data.get("land_category"),
            acquisition_status=parcel_data.get("acquisition_status"),
            total_award_amount=parcel_data.get("total_award_amount"),
            payment_status=parcel_data.get("payment_status"),
            landowner=parcel_data.get("landowner"),
            evidence_count=len(evidence_list),
            evidence_summary=ev_summaries,
            conflicts=conflict_dicts,
            anomalies=anomaly_resp.anomalies,
            anomaly_service_status=anomaly_resp.service_status,
            attention_categories=attention_flags,
            source="Authoritative PostgreSQL Database + Grounded RAG Documents"
        )

    def get_project_intelligence(self, project_id: str) -> ProjectIntelligenceResponse:
        # 1. Authoritative Project Parcel Facts
        parcels = self.db_service.get_authoritative_project_parcels(project_id)

        # 2. Scoped Retrieval Summary
        ret_req = RetrievalRequest(
            query=f"Project {project_id} document evidence summary",
            top_k=5,
            filters_override={"project_id": project_id}
        )
        ret_resp = self.retrieval_service.retrieve(ret_req)
        evidence_list = ret_resp.evidence or []

        # 3. Compute Deterministic Statistical Aggregates
        total_parcels = len(parcels)
        total_area = sum(p.get("area_hectares") or 0.0 for p in parcels)
        total_compensation = sum(p.get("total_award_amount") or 0.0 for p in parcels)

        stage_counts: Dict[str, int] = {}
        payment_counts: Dict[str, int] = {}
        village_counts: Dict[str, int] = {}

        proj_name = "Land Acquisition Project"
        proj_state = "Unknown"
        proj_district = "Unknown"

        for p in parcels:
            stg = p.get("acquisition_status") or "Pending Notification"
            stage_counts[stg] = stage_counts.get(stg, 0) + 1

            pmt = p.get("payment_status") or "Pending"
            payment_counts[pmt] = payment_counts.get(pmt, 0) + 1

            vil = p.get("village") or "Unknown"
            village_counts[vil] = village_counts.get(vil, 0) + 1

            if p.get("state"):
                proj_state = p.get("state")
            if p.get("district"):
                proj_district = p.get("district")

        # 4. Conflicts & Anomalies
        raw_conflicts = self.conflict_detector.detect_conflicts(parcels, evidence_list)
        anomaly_resp = self.anomaly_service.get_anomalies_for_project(project_id)

        # 5. Attention Flags (Zero predictive delay claims)
        attention_flags = self.attention_service.evaluate_project_attention(
            parcels=parcels,
            conflict_count=len(raw_conflicts),
            evidence_count=len(evidence_list),
            anomaly_count=len(anomaly_resp.anomalies)
        )

        return ProjectIntelligenceResponse(
            project_id=project_id,
            project_name=f"{project_id} - Land Acquisition Project",
            state=proj_state,
            district=proj_district,
            total_parcels=total_parcels,
            total_area_hectares=round(total_area, 4),
            total_awarded_compensation=round(total_compensation, 2),
            acquisition_stage_counts=stage_counts,
            payment_status_counts=payment_counts,
            village_counts=village_counts,
            evidence_count=len(evidence_list),
            conflict_count=len(raw_conflicts),
            anomaly_count=len(anomaly_resp.anomalies),
            anomaly_service_status=anomaly_resp.service_status,
            report_available=True, # Flag indicating report endpoint is available (does not trigger report gen)
            attention_categories=attention_flags,
            source="Authoritative PostgreSQL Database + Grounded RAG Documents"
        )
