import re
import json
import logging
from typing import Optional, Dict, Any
from backend.models.analytics import (
    AnalyticsRequest,
    AnalyticsFilter,
    OperationEnum,
    MetricFieldEnum,
    GroupByFieldEnum
)

logger = logging.getLogger(__name__)

# Allowlisted fields & values
ALLOWED_OPERATIONS = {"COUNT", "SUM", "AVG", "GROUP_BY", "LIST"}
ALLOWED_METRIC_FIELDS = {"parcel_id", "total_award_amount", "area_hectares", "case_id"}
ALLOWED_GROUP_BY_FIELDS = {"village", "district", "acquisition_status", "payment_status", "land_category"}

# Secondary safety blacklist keywords
MALICIOUS_SQL_KEYWORDS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b", r"\bALTER\b", r"\bTRUNCATE\b",
    r"\bEXEC\b", r"\bUNION\b", r"SELECT\s+\*", r"FROM\s+users\b", r"--", r";"
]


class AnalyticsQueryParser:
    """
    Parser for natural language analytical queries.
    Enforces a strict Pydantic AnalyticsRequest schema.
    NEVER generates or executes arbitrary SQL statements.
    """

    def __init__(self, llm_model: Optional[Any] = None):
        self.llm_model = llm_model

    def parse(self, query: str, scoped_project_id: Optional[str] = None) -> AnalyticsRequest:
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # 1. Secondary Security Check: Scan for malicious SQL injection patterns
        for pattern in MALICIOUS_SQL_KEYWORDS:
            if re.search(pattern, q_clean, re.IGNORECASE):
                logger.warning(f"Security Alert: Malicious or invalid pattern '{pattern}' detected in query.")
                return AnalyticsRequest(
                    query=query,
                    is_unsupported=True,
                    rejection_reason="Security Violation: Raw SQL statements or malicious injection payloads are strictly forbidden."
                )

        # 2. Check for completely unsupported non-analytical queries
        unsupported_keywords = ["predict", "delay score", "risk score", "python code", "who is", "weather"]
        if any(k in q_lower for k in unsupported_keywords):
            return AnalyticsRequest(
                query=query,
                is_unsupported=True,
                rejection_reason="Unsupported request: Only structured land acquisition analytics are supported."
            )

        # 3. Deterministic Regex Parsing
        request = self._parse_with_rules(q_clean, scoped_project_id)

        # 4. Fallback to LLM Structured Intent Parsing if rules were insufficient
        if request.is_ambiguous and self.llm_model:
            llm_request = self._parse_with_llm(q_clean, scoped_project_id)
            if llm_request and not llm_request.is_ambiguous:
                request = llm_request

        # 5. Final Schema Enforcement & Sanitization
        return self._sanitize_and_validate(request, scoped_project_id)

    def _parse_with_rules(self, query: str, scoped_project_id: Optional[str]) -> AnalyticsRequest:
        q_lower = query.lower()

        # Extract Project ID (Check explicit PRJ- prefix first)
        prj_match = re.search(r"\b(PRJ-[A-Z0-9\-_]+)\b", query, re.IGNORECASE)
        if not prj_match:
            prj_match = re.search(r"(?:project|prj)\s*:?\s*([A-Za-z0-9\-_]+)", query, re.IGNORECASE)
        project_id = prj_match.group(1).strip().upper() if prj_match else scoped_project_id

        # Extract Village
        village = None
        vil_match = re.search(r"(?:village|mauza)\s*:?\s*([A-Za-z]+)", query, re.IGNORECASE)
        if not vil_match:
            vil_match = re.search(r"in\s+([A-Z][a-z]+)\s+village", query)
        if vil_match:
            village = vil_match.group(1).strip().title()
        elif "vadadala" in q_lower:
            village = "Vadadala"
        elif "hinjewadi" in q_lower:
            village = "Hinjewadi"
        elif "wakad" in q_lower:
            village = "Wakad"
        elif "maan" in q_lower:
            village = "Maan"

        # Extract Acquisition Status Filter
        acquisition_status = None
        if "award pending" in q_lower:
            acquisition_status = "Award Pending"
        elif "section 19" in q_lower:
            acquisition_status = "Section 19 Notification Issued"
        elif "section 11" in q_lower:
            acquisition_status = "Section 11 Notification"
        elif "section 4" in q_lower:
            acquisition_status = "Section 4 Preliminary Notification"
        elif "possession" in q_lower and ("pending" in q_lower or "taken" in q_lower):
            acquisition_status = "Possession Pending" if "pending" in q_lower else "Possession Taken"

        # Extract Payment / Compensation Status Filter
        payment_status = None
        if "compensation pending" in q_lower or "payment pending" in q_lower or "unpaid" in q_lower:
            payment_status = "Pending"
        elif "compensation awarded" in q_lower or "paid" in q_lower or "calculated" in q_lower:
            payment_status = "Calculated"

        filters = AnalyticsFilter(
            project_id=project_id,
            village=village,
            acquisition_status=acquisition_status,
            payment_status=payment_status
        )

        # Detect Operation & Metrics
        operation = "COUNT"
        metric_field = "parcel_id"
        group_by_field = None
        is_ambiguous = False

        # Grouping intent
        if any(k in q_lower for k in ["which villages", "by village", "per village", "villages have"]):
            operation = "GROUP_BY"
            group_by_field = "village"
            if "compensation" in q_lower or "amount" in q_lower or "award" in q_lower:
                metric_field = "total_award_amount"
            else:
                metric_field = "parcel_id"
        elif any(k in q_lower for k in ["by status", "by acquisition status"]):
            operation = "GROUP_BY"
            group_by_field = "acquisition_status"
        elif any(k in q_lower for k in ["by payment", "by compensation status"]):
            operation = "GROUP_BY"
            group_by_field = "payment_status"
        # Aggregation intent
        elif any(k in q_lower for k in ["total awarded", "total compensation", "sum of compensation", "sum of award", "total award"]):
            operation = "SUM"
            metric_field = "total_award_amount"
        elif any(k in q_lower for k in ["average compensation", "avg award"]):
            operation = "AVG"
            metric_field = "total_award_amount"
        elif any(k in q_lower for k in ["how many parcels", "count of parcels", "number of parcels", "how many cases"]):
            operation = "COUNT"
            metric_field = "parcel_id"
        elif any(k in q_lower for k in ["show parcels", "list parcels"]):
            operation = "LIST"
            metric_field = "parcel_id"
        else:
            # Check if query is too vague
            if len(query.split()) < 3 and not project_id and not village:
                is_ambiguous = True

        return AnalyticsRequest(
            query=query,
            operation=operation,
            target_entity="parcels",
            metric_field=metric_field,
            group_by_field=group_by_field,
            filters=filters,
            project_id=project_id,
            is_ambiguous=is_ambiguous
        )

    def _parse_with_llm(self, query: str, scoped_project_id: Optional[str]) -> Optional[AnalyticsRequest]:
        prompt = f"""
You are an intent parser for a land acquisition database. Convert the user's question into structured JSON.
DO NOT write SQL. Output ONLY valid JSON matching this schema:

{{
  "operation": "COUNT" | "SUM" | "AVG" | "GROUP_BY" | "LIST",
  "target_entity": "parcels" | "compensation_awards",
  "metric_field": "parcel_id" | "total_award_amount" | "area_hectares",
  "group_by_field": null | "village" | "district" | "acquisition_status" | "payment_status",
  "filters": {{
    "project_id": null | string,
    "village": null | string,
    "district": null | string,
    "acquisition_status": null | string,
    "payment_status": null | string
  }},
  "is_ambiguous": boolean
}}

User Query: "{query}"
Context Project ID: "{scoped_project_id or ''}"

Output JSON:
"""
        try:
            raw_response = self.llm_model.generate(prompt)
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                filters_dict = data.get("filters") or {}
                if scoped_project_id and not filters_dict.get("project_id"):
                    filters_dict["project_id"] = scoped_project_id

                return AnalyticsRequest(
                    query=query,
                    operation=data.get("operation") or "COUNT",
                    target_entity=data.get("target_entity") or "parcels",
                    metric_field=data.get("metric_field") or "parcel_id",
                    group_by_field=data.get("group_by_field"),
                    filters=AnalyticsFilter(**filters_dict),
                    project_id=filters_dict.get("project_id"),
                    is_ambiguous=bool(data.get("is_ambiguous", False))
                )
        except Exception as e:
            logger.error(f"Error in LLM structured query parsing: {e}")

        return None


    def _sanitize_and_validate(self, req: AnalyticsRequest, scoped_project_id: Optional[str]) -> AnalyticsRequest:
        # Enforce allowlisted enum values
        if req.operation not in ALLOWED_OPERATIONS:
            req.operation = "COUNT"

        if req.metric_field and req.metric_field not in ALLOWED_METRIC_FIELDS:
            req.metric_field = "parcel_id"

        if req.group_by_field and req.group_by_field not in ALLOWED_GROUP_BY_FIELDS:
            req.group_by_field = None

        if scoped_project_id and not req.filters.project_id:
            req.filters.project_id = scoped_project_id

        if req.filters.project_id:
            req.project_id = req.filters.project_id

        return req
