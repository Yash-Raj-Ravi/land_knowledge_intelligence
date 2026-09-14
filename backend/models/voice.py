from typing import List, Optional
from pydantic import BaseModel, Field
from backend.models.rag import CitationItem
from backend.services.conflict_detector import ConflictItem


class STTResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed text string")
    language: str = Field("unknown", description="Language code e.g. en, hi, mr, unknown")
    provider: str = Field("sarvam", description="STT Provider name")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds")
    message: Optional[str] = Field(None, description="Status or message")


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize into speech")
    language: str = Field("en", description="Target language code: en, hi, or mr")


class TTSResponse(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio string (WAV)")
    language: str = Field("en", description="Synthesized language code")
    provider: str = Field("sarvam", description="TTS Provider name")
    format: str = Field("wav", description="Audio format")
    message: Optional[str] = Field(None, description="Status message or error detail")


class VoiceAskResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed query text")
    language: str = Field(..., description="Query language code (en, hi, mr)")
    answer: str = Field(..., description="Grounded RAG text answer")
    citations: List[CitationItem] = Field(default_factory=list, description="Source citations")
    evidence_coverage: str = Field("INSUFFICIENT", description="Evidence coverage status (COMPLETE | PARTIAL | INSUFFICIENT)")
    conflicts: List[ConflictItem] = Field(default_factory=list, description="Detected database vs document conflicts")
    audio_base64: Optional[str] = Field(None, description="Base64 audio response if TTS succeeded")
    audio_available: bool = Field(False, description="True if TTS audio output is attached")
