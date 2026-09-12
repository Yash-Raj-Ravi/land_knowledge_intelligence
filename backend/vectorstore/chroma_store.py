import chromadb
from backend.config import CHROMA_PATH, COLLECTION_NAME
import uuid
from collections import defaultdict
from typing import List, Dict, Any, Optional

class ChromaStore:
    def __init__(self, chroma_path: Optional[str] = None, collection_name: Optional[str] = None):
        path_str = str(chroma_path) if chroma_path else str(CHROMA_PATH)
        col_name = collection_name or COLLECTION_NAME
        self.client = chromadb.PersistentClient(path=path_str)
        self.collection = self.client.get_or_create_collection(col_name)

    def get_distance_metric(self) -> str:
        """Returns the actual distance metric configured in ChromaDB collection (default l2)."""
        meta = self.collection.metadata or {}
        return meta.get("hnsw:space", "l2")

    def add_land_chunk_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        doc_metadata: Any,
        file_path: str
    ) -> List[str]:
        documents = [c["text"] for c in chunks]
        embedding_vectors = embeddings

        metadatas = []
        ids = []

        for c in chunks:
            chunk_id_str = f"{doc_metadata.document_id}_{c['chunk_id']}"
            ids.append(chunk_id_str)

            chunk_surveys = c.get("survey_numbers", [])
            primary_survey = chunk_surveys[0] if chunk_surveys else (doc_metadata.survey_number or "")
            raw_s = c.get("raw_survey_number") or doc_metadata.survey_number or primary_survey
            norm_s = primary_survey or doc_metadata.survey_number or ""

            meta_dict = {
                "document_id": doc_metadata.document_id,
                "source_file": doc_metadata.source_file,
                "document_category": doc_metadata.document_category,
                "page_number": c.get("page_number", 1),
                "chunk_id": c["chunk_id"],
                "chunk_type": c.get("chunk_type", "prose"),
                "section_heading": c.get("section_heading", "General"),
                "raw_survey_number": raw_s,
                "normalized_survey_number": norm_s,
                "survey_number": norm_s,
                "survey_numbers_str": ", ".join(chunk_surveys),
                "language": doc_metadata.language,
                "file_path": file_path,
                "project_id": doc_metadata.project_id or "",
                "state": doc_metadata.state or "",
                "district": doc_metadata.district or "",
                "tehsil": doc_metadata.tehsil or "",
                "village": doc_metadata.village or "",
                "acquisition_stage": doc_metadata.acquisition_stage or "",
                "document_date": doc_metadata.document_date or "",
                "authority": doc_metadata.authority or ""
            }
            metadatas.append(meta_dict)

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embedding_vectors,
            metadatas=metadatas
        )

        return ids

    def filtered_similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes vector similarity search with explicit pre-filtering.
        Returns a dict containing:
          - 'results': raw Chroma query results
          - 'applied_filter': exact filter dict passed to Chroma
          - 'candidate_count': number of candidates returned
          - 'distance_metric': actual metric (l2 / cosine / ip)
        """
        metric = self.get_distance_metric()
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"]
        }
        
        # Valid Chroma metadata filter keys
        valid_keys = {
            "survey_number", "normalized_survey_number", "project_id",
            "village", "district", "tehsil", "state", "document_category",
            "acquisition_stage", "document_date", "document_id", "parcel_id"
        }

        cleaned_filter = {}
        if where_filter:
            for k, v in where_filter.items():
                if k in valid_keys and v is not None and str(v).strip() != "":
                    cleaned_filter[k] = str(v).strip()

        def build_chroma_where(filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not filter_dict:
                return None
            if len(filter_dict) == 1:
                return filter_dict
            return {"$and": [{k: v} for k, v in filter_dict.items()]}

        applied_filter = {}
        results = None

        if cleaned_filter:
            # 1. Try strict filter query
            applied_filter = cleaned_filter
            query_kwargs["where"] = build_chroma_where(cleaned_filter)
            results = self.collection.query(**query_kwargs)

            # Check if strict returned candidates
            docs = results.get("documents", [[]])[0] if results else []
            if len(docs) == 0:
                # 2. Relax filter: retain primary key (survey_number or project_id or village)
                relaxed_filter = {}
                for key in ["survey_number", "normalized_survey_number", "project_id", "village"]:
                    if key in cleaned_filter:
                        relaxed_filter[key] = cleaned_filter[key]
                        break

                if relaxed_filter:
                    applied_filter = relaxed_filter
                    query_kwargs["where"] = build_chroma_where(relaxed_filter)
                    results = self.collection.query(**query_kwargs)
                    docs = results.get("documents", [[]])[0] if results else []

                # 3. If still 0 results, fallback to un-filtered vector search
                if len(docs) == 0:
                    applied_filter = {}
                    query_kwargs.pop("where", None)
                    results = self.collection.query(**query_kwargs)
        else:
            query_kwargs.pop("where", None)
            results = self.collection.query(**query_kwargs)

        cand_docs = results.get("documents", [[]])[0] if results else []
        candidate_count = len(cand_docs)

        return {
            "results": results,
            "applied_filter": applied_filter,
            "candidate_count": candidate_count,
            "distance_metric": metric
        }



    def reset_database(self):
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    def list_documents(self):
        results = self.collection.get(include=["metadatas"])

        grouped_documents = defaultdict(
            lambda: {
                "document_id": "",
                "file_name": "",
                "document_type": "",
                "document_category": "",
                "total_chunks": 0,
            }
        )

        for metadata in results["metadatas"]:
            doc_id = metadata.get("document_id", "")
            document = grouped_documents[doc_id]
            document["document_id"] = doc_id
            document["file_name"] = metadata.get("source_file", "")
            document["document_type"] = metadata.get("document_category", "")
            document["document_category"] = metadata.get("document_category", "")
            document["total_chunks"] += 1

        documents = sorted(
            grouped_documents.values(),
            key=lambda doc: doc["file_name"].lower()
        )

        return {
            "total_documents": len(documents),
            "total_chunks": len(results["metadatas"]),
            "documents": documents
        }

    def get_file_path(self, document_id: str) -> str:
        results = self.collection.get(
            where={"document_id": document_id},
            include=["metadatas"]
        )

        if not results["metadatas"]:
            raise ValueError("Document not found")

        return results["metadatas"][0]["file_path"]

    def delete_document(self, document_id: str):
        self.collection.delete(
            where={"document_id": document_id}
        )


