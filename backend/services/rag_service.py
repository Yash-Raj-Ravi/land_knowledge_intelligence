import json
import re
import logging
from typing import List, Dict, Any, Optional

from backend.services.retrieval_service import RetrievalService
from backend.services.conflict_detector import ConflictDetector, ConflictItem
from backend.services.context_builder import ContextBuilder
from backend.services.llm_service import LLMService
from backend.models.retrieval import RetrievalRequest, RetrievalResponse, EvidenceSource
from backend.models.rag import AskRequest, AskResponse, CitationItem, RAGRequest, RAGResponse
from backend.utils.prompt_builder import build_land_rag_prompt

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        conflict_detector: ConflictDetector,
        context_builder: ContextBuilder,
        llm_service: LLMService,
    ):
        self.retrieval_service = retrieval_service
        self.conflict_detector = conflict_detector
        self.context_builder = context_builder
        self.llm_service = llm_service

    def ask(self, request: AskRequest) -> AskResponse:
        """
        Main Phase 3 Grounded RAG Generation Endpoint.
        """
        # 1. Phase 2 Retrieval Layer Execution
        retrieval_req = RetrievalRequest(
            query=request.query,
            top_k=request.top_k,
            project_id=request.project_id
        )
        retrieval_response: RetrievalResponse = self.retrieval_service.retrieve(retrieval_req)

        # 2. Deterministic Conflict Detection
        conflicts: List[ConflictItem] = self.conflict_detector.detect_conflicts(
            structured_records=retrieval_response.structured_records or [],
            evidence_list=retrieval_response.evidence or []
        )

        # 3. Context Construction
        context_str: str = self.context_builder.build_context(
            retrieval_response=retrieval_response,
            conflicts=conflicts
        )

        # 4. Prompt Generation
        prompt: str = build_land_rag_prompt(context=context_str, query=request.query)

        # 5. LLM Call #1
        raw_response = self.llm_service.generate_response(prompt)
        parsed_json = self._parse_json(raw_response)

        # 6. Controlled Repair Attempt if Malformed JSON
        if parsed_json is None:
            logger.warning("LLM response malformed JSON. Executing 1 controlled repair attempt...")
            repair_prompt = f"""{prompt}

==================================================
REPAIR INSTRUCTION:
Your previous response could not be parsed as valid JSON.
Please output ONLY a valid, well-formed JSON object matching the required schema exactly without markdown formatting or code blocks.
"""
            repair_response = self.llm_service.generate_response(repair_prompt)
            parsed_json = self._parse_json(repair_response)

        # 7. Safe Fallback if Repair Fails
        if parsed_json is None:
            logger.error("LLM repair attempt failed to produce valid JSON. Returning safe fallback.")
            return AskResponse(
                answer="Unable to parse structured LLM response safely.",
                citations=[],
                evidence_coverage=retrieval_response.evidence_coverage,
                conflicts=conflicts,
                retrieval_response=retrieval_response
            )

        # 8. Extract fields
        raw_answer = parsed_json.get("answer", "No answer provided.")
        raw_citations = parsed_json.get("citations", [])
        raw_coverage = parsed_json.get("evidence_coverage", retrieval_response.evidence_coverage)

        # 9. Citation Truth Validation against Phase 2 Evidence
        valid_citations = self._validate_citations(
            raw_citations=raw_citations,
            retrieved_evidence=retrieval_response.evidence or []
        )

        # Normalize coverage status
        if raw_coverage not in ["COMPLETE", "PARTIAL", "INSUFFICIENT"]:
            raw_coverage = retrieval_response.evidence_coverage

        return AskResponse(
            answer=raw_answer,
            citations=valid_citations,
            evidence_coverage=raw_coverage,
            conflicts=conflicts,
            retrieval_response=retrieval_response
        )

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        # Try direct json load first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try regex extract json block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group().strip())
            except json.JSONDecodeError:
                pass

        return None

    def _validate_citations(
        self,
        raw_citations: List[Any],
        retrieved_evidence: List[EvidenceSource]
    ) -> List[CitationItem]:
        """
        Validates citation document_ids against retrieved Phase 2 evidence objects.
        Rejects any citation whose document_id is not in retrieved evidence.
        """
        valid_citations: List[CitationItem] = []
        if not raw_citations or not isinstance(raw_citations, list):
            return valid_citations

        # Build set of valid doc_ids & file names from retrieval evidence
        valid_doc_ids = {ev.document_id for ev in retrieved_evidence if hasattr(ev, "document_id")}
        valid_files = {ev.file_name.lower() for ev in retrieved_evidence if hasattr(ev, "file_name")}

        evidence_by_doc_id = {ev.document_id: ev for ev in retrieved_evidence}
        evidence_by_file = {ev.file_name.lower(): ev for ev in retrieved_evidence}

        seen = set()

        for item in raw_citations:
            if not isinstance(item, dict):
                continue
            doc_id = str(item.get("document_id", "")).strip()
            file_name = str(item.get("file_name", "")).strip()
            page_num = item.get("page_number", 1)
            try:
                page_num = int(page_num)
            except (ValueError, TypeError):
                page_num = 1

            matched_ev = None
            if doc_id in valid_doc_ids:
                matched_ev = evidence_by_doc_id[doc_id]
            elif file_name.lower() in valid_files:
                matched_ev = evidence_by_file[file_name.lower()]

            if matched_ev:
                key = (matched_ev.document_id, matched_ev.file_name, page_num)
                if key not in seen:
                    seen.add(key)
                    valid_citations.append(CitationItem(
                        document_id=matched_ev.document_id,
                        file_name=matched_ev.file_name,
                        page_number=page_num if page_num > 0 else matched_ev.page_number
                    ))
            else:
                logger.warning(f"Rejected citation with document_id '{doc_id}' / file '{file_name}': not found in Phase 2 evidence.")

        return valid_citations

    # Legacy method wrapper for backward compatibility
    def answer_query(self, request: RAGRequest) -> RAGResponse:
        ask_req = AskRequest(query=request.query, top_k=request.top_k)
        ask_resp = self.ask(ask_req)
        return RAGResponse(
            answer=ask_resp.answer,
            citations=ask_resp.citations,
            evidence_coverage=ask_resp.evidence_coverage
        )







