import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseRanker(ABC):
    """Abstract interface for candidate chunk rankers."""
    
    @abstractmethod
    def rank_chunks(
        self,
        candidate_chunks: List[Dict[str, Any]],
        query_filters: Dict[str, Any],
        max_chunks_per_doc: int = 3
    ) -> List[Dict[str, Any]]:
        pass

class LandAcquisitionRanker(BaseRanker):
    """
    Deterministic land-acquisition-aware ranker.
    
    Priority Ordering (Multi-Key Tuple Sorting):
      1. Exact survey_number match (0 if matched / N/A, 1 if mismatched)
      2. Exact project_id match (0 if matched / N/A, 1 if mismatched)
      3. Document category or acquisition stage match (0 if matched / N/A, 1 if mismatched)
      4. Vector similarity distance (ascending)
      5. Document diversity constraint (max N chunks per document_id)
    """

    def rank_chunks(
        self,
        candidate_chunks: List[Dict[str, Any]],
        query_filters: Dict[str, Any],
        max_chunks_per_doc: int = 3
    ) -> List[Dict[str, Any]]:
        target_survey = query_filters.get("survey_number") or query_filters.get("normalized_survey_number")
        target_project = query_filters.get("project_id")
        target_category = query_filters.get("document_category")
        target_stage = query_filters.get("acquisition_stage")

        ranked_items = []
        for item in candidate_chunks:
            meta = item.get("metadata", {})
            text = item.get("text", "")
            dist = float(item.get("distance", 0.0))

            # Tier 1: Survey Match Key
            if target_survey:
                chunk_s = meta.get("normalized_survey_number") or meta.get("survey_number") or ""
                chunk_s_str = meta.get("survey_numbers_str", "")
                if target_survey.lower() in chunk_s.lower() or target_survey.lower() in chunk_s_str.lower() or target_survey.lower() in text.lower():
                    survey_key = 0
                else:
                    survey_key = 1
            else:
                survey_key = 0

            # Tier 2: Project Match Key
            if target_project:
                chunk_p = meta.get("project_id", "")
                if target_project.upper() == chunk_p.upper():
                    project_key = 0
                else:
                    project_key = 1
            else:
                project_key = 0

            # Tier 3: Document Category / Stage Match Key
            if target_category or target_stage:
                cat_match = target_category and target_category.lower() in meta.get("document_category", "").lower()
                stage_match = target_stage and target_stage.lower() in meta.get("acquisition_stage", "").lower()
                if cat_match or stage_match:
                    category_key = 0
                else:
                    category_key = 1
            else:
                category_key = 0

            sort_tuple = (survey_key, project_key, category_key, dist)
            ranked_items.append({
                "chunk": item,
                "sort_key": sort_tuple
            })

        # Deterministic multi-key sort
        ranked_items.sort(key=lambda x: x["sort_key"])

        # Tier 5: Document Diversity Filter
        final_chunks = []
        doc_counts: Dict[str, int] = {}
        for entry in ranked_items:
            chunk_obj = entry["chunk"]
            meta = chunk_obj.get("metadata", {})
            doc_id = meta.get("document_id", "unknown")

            if doc_counts.get(doc_id, 0) < max_chunks_per_doc:
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
                final_chunks.append(chunk_obj)

        return final_chunks
