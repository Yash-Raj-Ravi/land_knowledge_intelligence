import logging
from typing import Optional, Dict, Any, List
from backend.models.analytics import (
    AnalyticsRequest,
    AnalyticsResult,
    AnalyticsResultRow,
    AnalyticsResponse
)
from backend.analytics.query_parser import AnalyticsQueryParser
from backend.services.db_service import DatabaseService
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Executes natural language land acquisition analytics safely over PostgreSQL.
    Primary Security Boundary:
    - Never receives raw SQL from LLM.
    - Constructs parameterized SQL queries from allowlisted AnalyticsRequest fields.
    - PostgreSQL is authoritative. Demo in-memory store is offline fallback only.
    """

    def __init__(
        self,
        query_parser: AnalyticsQueryParser,
        db_service: DatabaseService,
        llm_service: Optional[LLMService] = None
    ):
        self.query_parser = query_parser
        self.db_service = db_service
        self.llm_service = llm_service

    def process_query(self, query: str, project_id: Optional[str] = None) -> AnalyticsResponse:
        # 1. Parse into validated AnalyticsRequest schema
        parsed_req = self.query_parser.parse(query, scoped_project_id=project_id)

        # 2. Reject unsupported or malicious queries safely
        if parsed_req.is_unsupported:
            return AnalyticsResponse(
                query=query,
                parsed_request=parsed_req,
                result=AnalyticsResult(operation=parsed_req.operation, row_count=0),
                summary_explanation=f"Query Rejected: {parsed_req.rejection_reason or 'Unsupported analytical query.'}",
                source="Authoritative PostgreSQL Database",
                is_valid_analytical_query=False,
                error_message=parsed_req.rejection_reason
            )

        if parsed_req.is_ambiguous:
            return AnalyticsResponse(
                query=query,
                parsed_request=parsed_req,
                result=AnalyticsResult(operation=parsed_req.operation, row_count=0),
                summary_explanation="Ambiguous Query: Please specify a project, village, or analytical metric (e.g. count of parcels, total compensation, group by village).",
                source="Authoritative PostgreSQL Database",
                is_valid_analytical_query=False,
                error_message="Ambiguous request."
            )

        # 3. Deterministic Parameterized SQL Execution
        result = self._execute_analytical_request(parsed_req)

        # 4. Generate natural-language summary of database facts
        summary = self._generate_explanation(query, parsed_req, result)

        return AnalyticsResponse(
            query=query,
            parsed_request=parsed_req,
            result=result,
            summary_explanation=summary,
            source=result.execution_source,
            is_valid_analytical_query=True
        )

    def _execute_analytical_request(self, req: AnalyticsRequest) -> AnalyticsResult:
        conn = self.db_service.get_connection()
        if conn:
            try:
                return self._execute_postgres_query(conn, req)
            except Exception as e:
                logger.error(f"PostgreSQL query execution failed, falling back to in-memory store: {e}")
            finally:
                conn.close()

        # Offline / Demo Fallback Execution
        return self._execute_in_memory_fallback(req)

    def _execute_postgres_query(self, conn, req: AnalyticsRequest) -> AnalyticsResult:
        with conn.cursor() as cur:
            where_clauses = []
            params = []

            filters = req.filters
            if filters.project_id:
                where_clauses.append("UPPER(v.project_id) = UPPER(%s)")
                params.append(filters.project_id)
            if filters.village:
                where_clauses.append("LOWER(v.name) = LOWER(%s)")
                params.append(filters.village)
            if filters.district:
                where_clauses.append("LOWER(v.district) = LOWER(%s)")
                params.append(filters.district)
            if filters.acquisition_status:
                where_clauses.append("LOWER(p.acquisition_status) LIKE LOWER(%s)")
                params.append(f"%{filters.acquisition_status}%")
            if filters.payment_status:
                where_clauses.append("LOWER(ca.payment_status) LIKE LOWER(%s)")
                params.append(f"%{filters.payment_status}%")

            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            applied_filters = {
                k: v for k, v in req.filters.model_dump().items() if v is not None
            }

            # A. COUNT Operation
            if req.operation == "COUNT":
                sql = f"""
                    SELECT COUNT(DISTINCT p.parcel_id)
                    FROM parcels p
                    JOIN villages v ON p.village_id = v.village_id
                    LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                    {where_sql};
                """
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                val = row[0] if row else 0
                return AnalyticsResult(
                    operation="COUNT",
                    target_entity=req.target_entity,
                    metric_field=req.metric_field or "parcel_id",
                    aggregate_value=float(val),
                    row_count=1,
                    rows=[{"count": val}],
                    applied_filters=applied_filters,
                    execution_source="Authoritative PostgreSQL Database"
                )

            # B. SUM Operation
            elif req.operation == "SUM":
                sql = f"""
                    SELECT COALESCE(SUM(ca.total_award_amount), 0)
                    FROM parcels p
                    JOIN villages v ON p.village_id = v.village_id
                    LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                    {where_sql};
                """
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                val = float(row[0]) if row else 0.0
                return AnalyticsResult(
                    operation="SUM",
                    target_entity=req.target_entity,
                    metric_field=req.metric_field or "total_award_amount",
                    aggregate_value=val,
                    row_count=1,
                    rows=[{"sum": val}],
                    applied_filters=applied_filters,
                    execution_source="Authoritative PostgreSQL Database"
                )

            # C. AVG Operation
            elif req.operation == "AVG":
                sql = f"""
                    SELECT COALESCE(AVG(ca.total_award_amount), 0)
                    FROM parcels p
                    JOIN villages v ON p.village_id = v.village_id
                    LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                    {where_sql};
                """
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                val = float(row[0]) if row else 0.0
                return AnalyticsResult(
                    operation="AVG",
                    target_entity=req.target_entity,
                    metric_field=req.metric_field or "total_award_amount",
                    aggregate_value=val,
                    row_count=1,
                    rows=[{"avg": val}],
                    applied_filters=applied_filters,
                    execution_source="Authoritative PostgreSQL Database"
                )

            # D. GROUP_BY Operation
            elif req.operation == "GROUP_BY":
                group_col = "v.name"
                if req.group_by_field == "acquisition_status":
                    group_col = "p.acquisition_status"
                elif req.group_by_field == "payment_status":
                    group_col = "COALESCE(ca.payment_status, 'Pending')"
                elif req.group_by_field == "district":
                    group_col = "v.district"
                elif req.group_by_field == "land_category":
                    group_col = "p.land_category"

                sql = f"""
                    SELECT {group_col} as group_key,
                           COUNT(DISTINCT p.parcel_id) as parcel_count,
                           COALESCE(SUM(ca.total_award_amount), 0) as metric_sum
                    FROM parcels p
                    JOIN villages v ON p.village_id = v.village_id
                    LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                    {where_sql}
                    GROUP BY {group_col}
                    ORDER BY parcel_count DESC, metric_sum DESC;
                """
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                parsed_rows = []
                for r in rows:
                    parsed_rows.append({
                        "group_key": r[0] or "Unknown",
                        "count": r[1],
                        "total_award_amount": float(r[2]) if r[2] is not None else 0.0
                    })
                return AnalyticsResult(
                    operation="GROUP_BY",
                    target_entity=req.target_entity,
                    metric_field=req.metric_field,
                    group_by_field=req.group_by_field,
                    row_count=len(parsed_rows),
                    rows=parsed_rows,
                    applied_filters=applied_filters,
                    execution_source="Authoritative PostgreSQL Database"
                )

            # E. LIST Operation
            else:
                sql = f"""
                    SELECT p.parcel_id, p.survey_number, v.name as village,
                           p.area_hectares, p.acquisition_status,
                           ca.total_award_amount, COALESCE(ca.payment_status, 'Pending') as payment_status
                    FROM parcels p
                    JOIN villages v ON p.village_id = v.village_id
                    LEFT JOIN compensation_awards ca ON ca.parcel_id = p.parcel_id
                    {where_sql}
                    LIMIT 50;
                """
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                parsed_rows = []
                for r in rows:
                    parsed_rows.append({
                        "parcel_id": r[0],
                        "survey_number": r[1],
                        "village": r[2],
                        "area_hectares": float(r[3]) if r[3] is not None else None,
                        "acquisition_status": r[4],
                        "total_award_amount": float(r[5]) if r[5] is not None else None,
                        "payment_status": r[6]
                    })
                return AnalyticsResult(
                    operation="LIST",
                    target_entity=req.target_entity,
                    row_count=len(parsed_rows),
                    rows=parsed_rows,
                    applied_filters=applied_filters,
                    execution_source="Authoritative PostgreSQL Database"
                )

    def _execute_in_memory_fallback(self, req: AnalyticsRequest) -> AnalyticsResult:
        # Fallback using DatabaseService in-memory parcel structures
        all_parcels = self.db_service.list_all_parcels(
            project_id=req.filters.project_id,
            village=req.filters.village
        )

        # Apply in-memory filtering
        filtered = []
        for p in all_parcels:
            if req.filters.acquisition_status and req.filters.acquisition_status.lower() not in p.get("acquisition_status", "").lower():
                continue
            if req.filters.payment_status and req.filters.payment_status.lower() not in p.get("payment_status", "").lower():
                continue
            filtered.append(p)

        applied_filters = {k: v for k, v in req.filters.model_dump().items() if v is not None}
        source_label = "Demo In-Memory Store (Offline Fallback)"

        if req.operation == "COUNT":
            return AnalyticsResult(
                operation="COUNT",
                target_entity=req.target_entity,
                metric_field="parcel_id",
                aggregate_value=float(len(filtered)),
                row_count=1,
                rows=[{"count": len(filtered)}],
                applied_filters=applied_filters,
                execution_source=source_label
            )

        elif req.operation == "SUM":
            total_sum = sum(p.get("total_award_amount") or 0.0 for p in filtered)
            return AnalyticsResult(
                operation="SUM",
                target_entity=req.target_entity,
                metric_field="total_award_amount",
                aggregate_value=float(total_sum),
                row_count=1,
                rows=[{"sum": total_sum}],
                applied_filters=applied_filters,
                execution_source=source_label
            )

        elif req.operation == "AVG":
            total_sum = sum(p.get("total_award_amount") or 0.0 for p in filtered)
            avg_val = total_sum / len(filtered) if filtered else 0.0
            return AnalyticsResult(
                operation="AVG",
                target_entity=req.target_entity,
                metric_field="total_award_amount",
                aggregate_value=float(avg_val),
                row_count=1,
                rows=[{"avg": avg_val}],
                applied_filters=applied_filters,
                execution_source=source_label
            )

        elif req.operation == "GROUP_BY":
            grouped = {}
            for p in filtered:
                key = p.get("village", "Unknown")
                if req.group_by_field == "acquisition_status":
                    key = p.get("acquisition_status", "Unknown")
                elif req.group_by_field == "payment_status":
                    key = p.get("payment_status", "Pending")

                if key not in grouped:
                    grouped[key] = {"count": 0, "total_award_amount": 0.0}
                grouped[key]["count"] += 1
                grouped[key]["total_award_amount"] += (p.get("total_award_amount") or 0.0)

            parsed_rows = [
                {"group_key": k, "count": v["count"], "total_award_amount": v["total_award_amount"]}
                for k, v in grouped.items()
            ]
            parsed_rows.sort(key=lambda x: x["count"], reverse=True)

            return AnalyticsResult(
                operation="GROUP_BY",
                target_entity=req.target_entity,
                group_by_field=req.group_by_field,
                row_count=len(parsed_rows),
                rows=parsed_rows,
                applied_filters=applied_filters,
                execution_source=source_label
            )

        else:
            return AnalyticsResult(
                operation="LIST",
                target_entity=req.target_entity,
                row_count=len(filtered),
                rows=filtered,
                applied_filters=applied_filters,
                execution_source=source_label
            )

    def _generate_explanation(self, query: str, req: AnalyticsRequest, res: AnalyticsResult) -> str:
        # Generate clear natural language summary of computed database facts
        filters_str = ""
        if res.applied_filters:
            f_parts = [f"{k}: '{v}'" for k, v in res.applied_filters.items()]
            filters_str = f" (Filters: {', '.join(f_parts)})"

        if res.operation == "COUNT":
            val = int(res.aggregate_value) if res.aggregate_value is not None else 0
            return f"Found **{val}** matching parcel(s){filters_str} in the database."

        elif res.operation == "SUM":
            val = res.aggregate_value or 0.0
            return f"The total awarded compensation for matching parcel(s){filters_str} is **₹{val:,.2f}**."

        elif res.operation == "AVG":
            val = res.aggregate_value or 0.0
            return f"The average awarded compensation for matching parcel(s){filters_str} is **₹{val:,.2f}**."

        elif res.operation == "GROUP_BY":
            top_groups = []
            for r in res.rows[:3]:
                top_groups.append(f"**{r.get('group_key')}**: {r.get('count')} parcels (₹{r.get('total_award_amount', 0):,.2f})")
            summary_str = "; ".join(top_groups) if top_groups else "No grouped records found."
            return f"Analytics grouped by **{res.group_by_field or 'village'}**{filters_str}: {summary_str}."

        else:
            return f"Retrieved **{res.row_count}** parcel record(s){filters_str} from the authoritative database."
