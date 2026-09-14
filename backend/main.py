from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
import shutil
import os,uuid
import logging
from .services.chunk_service import ChunkService
from .services.document_service import DocumentService
from .services.embedding_service import EmbeddingService
from .services.search_service import SearchService
from .services.repository_service import RepositoryService
from .services.entity_service import EntityService
from .vectorstore.chroma_store import ChromaStore
from .models.rag import RAGResponse, RAGRequest, AskRequest, AskResponse
from .models.repository import DeleteDocumentResponse
from .models.search import SearchResponse, SearchRequest
from .config import ALLOWED_TYPES, UPLOAD_DIR
from pydantic import BaseModel
from .models.embedding import EmbedResponse, ResetResponse
from .models.land_metadata import LandEmbedRequest
from .services.classification_service import ClassificationService
from .services.rag_service import RAGService
from backend.models.entities import EntityRequest, EntityResponse

# Services
from .core.dependencies import (
    get_document_service,
    get_chunk_service,
    get_embedding_service,
    get_chroma_store,
    get_search_service,
    get_entity_service,
    get_rag_service,
    get_repository_service,
    get_db_service,
    get_classification_service,
    get_analytics_service,
    get_report_service,
    get_intelligence_service,
    get_voice_service
)
from .services.db_service import DatabaseService
from .services.analytics_service import AnalyticsService
from .services.report_service import ReportService
from .services.intelligence_service import IntelligenceService
from .services.voice_service import VoiceService
from .models.analytics import AnalyticsResponse, AnalyticsRequest
from .models.report import ProjectReportRequest, ProjectReportResponse
from .models.intelligence import ParcelIntelligenceResponse, ProjectIntelligenceResponse
from .models.voice import STTResponse, TTSRequest, TTSResponse, VoiceAskResponse


from typing import Optional

class AnalyticsQueryInput(BaseModel):
    query: str

    project_id: Optional[str] = None


logger = logging.getLogger(__name__)

from .models.repository import RepositoryResponse
from .services.repository_service import RepositoryService

app = FastAPI(
    title="Industrial Knowledge Intelligence API",
    description="Backend API for Industrial Knowledge Intelligence Platform",
    version="1.0"
    )


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class FilePathRequest(BaseModel):
    file_path: str
@app.get("/")
def home():
    return {"message":"Industrial-knowledge-intelligence API is running",
             "status":"success"}

import hashlib
from .services.table_extractor import TableScheduleExtractor

table_extractor = TableScheduleExtractor()

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = file.file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as destination:
        destination.write(content)

    return {
        "message": "File is uploaded successfully",
        "file_name": file.filename,
        "content_type": file.content_type,
        "path": str(file_path),
        "file_hash": file_hash
    }

@app.post("/embed", response_model=EmbedResponse)
def embed_endpoint(
    request: LandEmbedRequest,
    document_service = Depends(get_document_service),
    chunk_service: ChunkService = Depends(get_chunk_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    classification_service: ClassificationService = Depends(get_classification_service),
    db_service: DatabaseService = Depends(get_db_service),
    store: ChromaStore = Depends(get_chroma_store)
):
    try:
        file_name = os.path.basename(request.file_path)
        
        # 1. Compute SHA-256 File Hash
        with open(request.file_path, "rb") as f:
            file_bytes = f.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 2. Check Duplicate Document Purge
        existing_doc = db_service.get_document_by_hash(file_hash)
        if existing_doc:
            old_doc_id = existing_doc["document_id"]
            logger.info(f"Duplicate document detected (Hash: {file_hash[:10]}...). Purging existing vectors for doc {old_doc_id}.")
            try:
                store.delete_document(old_doc_id)
            except Exception as e:
                logger.warning(f"Error purging old ChromaDB vectors: {e}")
            document_id = old_doc_id
        else:
            document_id = str(uuid.uuid4())

        # 3. Parse Raw Text with Page Markers
        raw_text = document_service.parse_document(request.file_path)

        # 4. Hybrid Classification & Metadata Extraction
        user_overrides = {
            "project_id": request.project_id,
            "document_category": request.document_category,
            "village": request.village,
            "survey_number": request.survey_number
        }
        doc_metadata = classification_service.process_document_metadata(
            text=raw_text,
            document_id=document_id,
            source_file=file_name,
            user_overrides=user_overrides
        )

        # 5. Extract Structured Land Schedule Tables (Area, Owners, Compensation)
        structured_parcels = table_extractor.extract_structured_parcels(raw_text)

        # 6. Persist Authoritative Metadata & Structured Parcel Records into PostgreSQL
        db_service.persist_document_metadata(doc_metadata, request.file_path, file_hash)
        if structured_parcels:
            db_service.persist_structured_parcels(doc_metadata, structured_parcels, request.file_path)

        # 7. Structure-Aware Chunking
        chunks = chunk_service.chunk_document(request.file_path, doc_metadata)

        # 8. Generate Batch Embeddings
        chunk_texts = [c["text"] for c in chunks]
        batch_embeddings = embedding_service.embedding_model.embed_texts(chunk_texts)
        dimension = len(batch_embeddings[0]) if batch_embeddings else 1024

        # 9. Persistent Index in ChromaDB with full metadata
        store.add_land_chunk_embeddings(
            chunks=chunks,
            embeddings=batch_embeddings,
            doc_metadata=doc_metadata,
            file_path=request.file_path
        )

        msg = f"Indexed document as '{doc_metadata.document_category}' ({len(structured_parcels)} structured parcel records)."
        return EmbedResponse(
            message=msg,
            total_chunks=len(chunks),
            embedding_dimension=dimension
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/extract-entities", response_model=EntityResponse)
def extract_entities_endpoint(
    request: EntityRequest,
    repository_service: RepositoryService = Depends(get_repository_service),
    document_service=Depends(get_document_service),
    entity_service=Depends(get_entity_service)
):
    try:
        file_path = repository_service.get_file_path(request.document_id)

        document_text = document_service.parse_document(file_path)

        entities = entity_service.extract_entities(document_text)

        return EntityResponse(
            message="Entities extracted successfully.",
            entities=entities
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract entities: {str(e)}"
        )
from .models.retrieval import RetrievalRequest, RetrievalResponse
from .core.dependencies import get_retrieval_service
from .services.retrieval_service import RetrievalService

@app.post("/retrieve", response_model=RetrievalResponse)
def retrieve_endpoint(
    request: RetrievalRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    try:
        return retrieval_service.retrieve(request)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    try:
        return rag_service.ask(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects")
def projects_endpoint(
    db_service: DatabaseService = Depends(get_db_service)
):
    try:
        return db_service.list_all_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parcels")
def parcels_endpoint(
    project_id: Optional[str] = None,
    village: Optional[str] = None,
    db_service: DatabaseService = Depends(get_db_service)
):
    try:
        return db_service.list_all_parcels(project_id=project_id, village=village)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/query", response_model=AnalyticsResponse)
def analytics_query_endpoint(
    input_data: AnalyticsQueryInput,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    try:
        return analytics_service.process_query(input_data.query, project_id=input_data.project_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reports/project", response_model=ProjectReportResponse)
def project_report_endpoint(
    request: ProjectReportRequest,
    report_service: ReportService = Depends(get_report_service)
):
    try:
        return report_service.generate_project_report(request.project_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parcels/{parcel_id:path}/intelligence", response_model=ParcelIntelligenceResponse)
def parcel_intelligence_endpoint(
    parcel_id: str,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service)
):
    try:
        return intelligence_service.get_parcel_intelligence(parcel_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/intelligence", response_model=ProjectIntelligenceResponse)
def project_intelligence_endpoint(
    project_id: str,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service)
):
    try:
        return intelligence_service.get_project_intelligence(project_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/transcribe", response_model=STTResponse)
def voice_transcribe_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form("auto"),
    voice_service: VoiceService = Depends(get_voice_service)
):
    try:
        audio_bytes = file.file.read()
        return voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language or "auto"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/synthesize", response_model=TTSResponse)
def voice_synthesize_endpoint(
    request: TTSRequest,
    voice_service: VoiceService = Depends(get_voice_service)
):
    try:
        return voice_service.synthesize(
            text=request.text,
            language=request.language
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/ask", response_model=VoiceAskResponse)
def voice_ask_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form("auto"),
    project_id: Optional[str] = Form(None),
    parcel_id: Optional[str] = Form(None),
    survey_number: Optional[str] = Form(None),
    village: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    voice_service: VoiceService = Depends(get_voice_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    try:
        audio_bytes = file.file.read()
        stt_res = voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language or "auto"
        )

        if not stt_res.transcript or stt_res.provider == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Speech recognition failed: {stt_res.message or 'No transcript produced'}"
            )

        resp_lang = stt_res.language if stt_res.language not in ["unknown", "auto"] else (language if language != "auto" else "en")

        ask_req = AskRequest(
            query=stt_res.transcript,
            project_id=project_id,
            parcel_id=parcel_id,
            survey_number=survey_number,
            village=village,
            district=district,
            response_language=resp_lang
        )

        rag_res = rag_service.ask(ask_req)

        tts_res = voice_service.synthesize(text=rag_res.answer, language=resp_lang)

        return VoiceAskResponse(
            transcript=stt_res.transcript,
            language=resp_lang,
            answer=rag_res.answer,
            citations=rag_res.citations,
            evidence_coverage=rag_res.evidence_coverage,
            conflicts=rag_res.conflicts,
            audio_base64=tts_res.audio_base64,
            audio_available=bool(tts_res.audio_base64)
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))








@app.get(
    "/documents",
    response_model=RepositoryResponse
)
def documents_endpoint(
    repository_service: RepositoryService = Depends(get_repository_service)
):
    try:
        return repository_service.get_repository()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Development utility endpoint.
# Clears the entire ChromaDB collection.
@app.post("/reset", response_model=ResetResponse)
def reset_database_endpoint(store: ChromaStore = Depends(get_chroma_store)):
    try:
        store.reset_database()

        return ResetResponse(
            message="Vector database reset successfully."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse
)
def delete_document_endpoint(
    document_id: str,
    repository_service: RepositoryService = Depends(get_repository_service)
):
    try:
        repository_service.delete_document(document_id)

        return DeleteDocumentResponse(
            message="Document deleted successfully."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

