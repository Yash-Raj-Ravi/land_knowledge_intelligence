import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Allowed Attention Categories
ATTENTION_CATEGORIES = [
    "DATA_CONFLICT",
    "ANOMALY_DETECTED",
    "COMPENSATION_PENDING",
    "POSSESSION_PENDING",
    "R_AND_R_PENDING",
    "DOCUMENT_MISSING",
    "VERIFICATION_REQUIRED"
]


class AttentionService:
    """
    Deterministic Current-State Attention Summarizer.
    Evaluates current database facts, conflicts, evidence, and anomalies to assign attention flags.
    CRITICAL SAFETY: Does NOT compute delay probabilities, predicted delay days, or future risk scores.
    """

    def evaluate_parcel_attention(
        self,
        parcel_data: Dict[str, Any],
        conflicts: List[Any],
        evidence_list: List[Any],
        anomalies: List[Any]
    ) -> List[str]:
        attention_flags = []

        # 1. DATA_CONFLICT
        if conflicts:
            attention_flags.append("DATA_CONFLICT")

        # 2. ANOMALY_DETECTED
        open_anomalies = [a for a in anomalies if getattr(a, "status", "open") == "open"]
        if open_anomalies:
            attention_flags.append("ANOMALY_DETECTED")

        # 3. COMPENSATION_PENDING
        pmt = parcel_data.get("payment_status", "").lower() if parcel_data else ""
        if pmt in ["pending", "calculated", "unpaid"]:
            attention_flags.append("COMPENSATION_PENDING")

        # 4. POSSESSION_PENDING
        acq = parcel_data.get("acquisition_status", "").lower() if parcel_data else ""
        if "possession" in acq and "taken" not in acq:
            attention_flags.append("POSSESSION_PENDING")
        elif "notification" in acq or "declaration" in acq or "pending" in acq:
            attention_flags.append("POSSESSION_PENDING")

        # 5. R_AND_R_PENDING
        has_rr_record = any("r&r" in str(getattr(ev, "section_heading", "")).lower() for ev in evidence_list)
        if not has_rr_record:
            attention_flags.append("R_AND_R_PENDING")

        # 6. DOCUMENT_MISSING
        if not evidence_list:
            attention_flags.append("DOCUMENT_MISSING")

        # 7. VERIFICATION_REQUIRED
        if conflicts or len(open_anomalies) > 0 or not parcel_data.get("landowner"):
            attention_flags.append("VERIFICATION_REQUIRED")

        return attention_flags

    def evaluate_project_attention(
        self,
        parcels: List[Dict[str, Any]],
        conflict_count: int,
        evidence_count: int,
        anomaly_count: int
    ) -> List[str]:
        flags = []
        if conflict_count > 0:
            flags.append("DATA_CONFLICT")
        if anomaly_count > 0:
            flags.append("ANOMALY_DETECTED")

        has_pending_comp = any(
            p.get("payment_status", "").lower() in ["pending", "calculated"]
            for p in parcels
        )
        if has_pending_comp:
            flags.append("COMPENSATION_PENDING")

        if evidence_count == 0:
            flags.append("DOCUMENT_MISSING")

        if conflict_count > 0 or anomaly_count > 0:
            flags.append("VERIFICATION_REQUIRED")

        return flags
