import logging
from typing import Dict, Any, List, Optional
from backend.services.query_parser import QueryParser
from backend.services.embedding_service import EmbeddingService
from backend.services.db_service import DatabaseService
from backend.vectorstore.chroma_store import ChromaStore
from backend.services.ranker import BaseRanker, LandAcquisitionRanker
from backend.models.retrieval import RetrievalRequest, RetrievalResponse, EvidenceSource

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(
        self,
        query_parser: QueryParser,
        embedding_service: EmbeddingService,
        db_service: DatabaseService,
        store: ChromaStore,
        ranker: Optional[BaseRanker] = None
    ):
        self.query_parser = query_parser
        self.embedding_service = embedding_service
        self.db_service = db_service
        self.store = store
        self.ranker = ranker or LandAcquisitionRanker()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_text = request.query.strip()

        # 1. Query Understanding & Deterministic Metadata Extraction
        parsed_filters = self.query_parser.parse_query_filters(query_text)
        
        effective_filters = dict(parsed_filters)
        if request.filters_override:
            for k, v in request.filters_override.items():
                if v is not None and str(v).strip() != "":
                    effective_filters[k] = v

        # 2. PostgreSQL Authoritative Structured Lookup
        structured_records: List[Dict[str, Any]] = []
        target_survey = effective_filters.get("normalized_survey_number") or effective_filters.get("survey_number")
        target_village = effective_filters.get("village") or ""
        target_project = effective_filters.get("project_id")

        if target_survey:
            pg_record = self.db_service.get_authoritative_parcel_data(target_village, target_survey)
            if pg_record:
                structured_records.append(pg_record)
        elif target_project:
            proj_records = self.db_service.get_authoritative_project_parcels(target_project)
            structured_records.extend(proj_records)

        # 3. Vector Search with Explicit Metadata Pre-Filtering
        query_embedding = self.embedding_service.generate_query_embedding(query_text)
        
        search_res = self.store.filtered_similarity_search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            where_filter=effective_filters
        )

        raw_chroma = search_res.get("results", {})
        applied_filters = search_res.get("applied_filter", {})
        candidate_count = search_res.get("candidate_count", 0)
        distance_metric = search_res.get("distance_metric", "l2")

        raw_documents = raw_chroma.get("documents", [[]])[0] if raw_chroma else []
        raw_metadatas = raw_chroma.get("metadatas", [[]])[0] if raw_chroma else []
        raw_distances = raw_chroma.get("distances", [[]])[0] if raw_chroma else []

        candidate_chunks = []
        for doc_text, meta, dist in zip(raw_documents, raw_metadatas, raw_distances):
            candidate_chunks.append({
                "text": doc_text,
                "metadata": meta,
                "distance": float(dist)
            })

        # 4. Modular Deterministic Ranking
        ranked_chunks = self.ranker.rank_chunks(
            candidate_chunks=candidate_chunks,
            query_filters=effective_filters,
            max_chunks_per_doc=3
        )

        # 5. Citation & Evidence Model Construction
        evidence_list: List[EvidenceSource] = []
        retrieved_chunk_dicts: List[Dict[str, Any]] = []

        for item in ranked_chunks:
            meta = item["metadata"]
            ev = EvidenceSource(
                document_id=meta.get("document_id", ""),
                file_name=meta.get("source_file", meta.get("file_name", "document.pdf")),
                page_number=int(meta.get("page_number", 1)),
                section_heading=meta.get("section_heading", "General Section"),
                chunk_id=int(meta.get("chunk_id", 1)),
                raw_survey_number=meta.get("raw_survey_number"),
                survey_number=meta.get("normalized_survey_number") or meta.get("survey_number"),
                project_id=meta.get("project_id"),

                excerpt=item["text"],
                distance=float(item["distance"]),
                distance_metric=distance_metric
            )
            evidence_list.append(ev)
            retrieved_chunk_dicts.append({
                "chunk_id": ev.chunk_id,
                "document_id": ev.document_id,
                "file_name": ev.file_name,
                "page_number": ev.page_number,
                "section_heading": ev.section_heading,
                "text": item["text"],
                "distance": ev.distance,
                "distance_metric": distance_metric
            })

        # 6. Evaluate Evidence Coverage Strictly
        has_rel_filter = parsed_filters.get("has_reliable_filter", False)
        retrieved_count = len(evidence_list)

        # Check if retrieved chunks match target query filters
        matching_survey_chunks = [
            ev for ev in evidence_list
            if target_survey and (
                (ev.survey_number and target_survey.lower() in ev.survey_number.lower())
                or (target_survey.lower() in ev.excerpt.lower())
            )
        ]
        matching_project_chunks = [
            ev for ev in evidence_list
            if target_project and ev.project_id and target_project.upper() == ev.project_id.upper()
        ]

        if target_survey:
            if structured_records and len(matching_survey_chunks) > 0:
                coverage = "COMPLETE"
            elif structured_records or len(matching_survey_chunks) > 0:
                coverage = "PARTIAL"
            else:
                coverage = "INSUFFICIENT"
        elif target_project:
            if len(matching_project_chunks) > 0 or len(structured_records) > 0:
                coverage = "COMPLETE"
            else:
                coverage = "INSUFFICIENT"
        elif effective_filters.get("village"):
            matching_village_chunks = [
                ev for ev in evidence_list
                if effective_filters["village"].lower() in ev.excerpt.lower() or effective_filters["village"].lower() in ev.file_name.lower()
            ]
            if len(matching_village_chunks) > 0:
                coverage = "COMPLETE"
            elif retrieved_count > 0:
                coverage = "PARTIAL"
            else:
                coverage = "INSUFFICIENT"
        elif retrieved_count > 0 or len(structured_records) > 0:
            coverage = "COMPLETE" if retrieved_count >= 2 else "PARTIAL"
        else:
            coverage = "INSUFFICIENT"

        ranking_method_name = "Deterministic (Exact Survey > Exact Project > Category/Stage > Distance > Diversity)"

        return RetrievalResponse(
            query=query_text,
            parsed_filters=parsed_filters,
            applied_filters=applied_filters,
            filters=effective_filters,
            structured_records=structured_records,
            retrieved_chunks=retrieved_chunk_dicts,
            evidence=evidence_list,
            candidate_count=candidate_count,
            retrieved_count=retrieved_count,
            ranking_method=ranking_method_name,
            distance_metric=distance_metric,
            supporting_source_count=retrieved_count,
            evidence_coverage=coverage,
            reliable_filter_found=has_rel_filter
        )


