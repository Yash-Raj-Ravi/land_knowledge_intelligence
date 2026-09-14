import io
import os
import logging
import base64
import binascii
import json
import requests
from abc import ABC, abstractmethod
from typing import Optional, List
from dotenv import load_dotenv

from backend.models.voice import STTResponse, TTSResponse

load_dotenv()
logger = logging.getLogger(__name__)

# Land Domain Keyterm Allowlist for Saaras / Saarika STT
LAND_DOMAIN_KEYTERMS: List[str] = [
    "khasra",
    "7/12",
    "bhusampadan",
    "mobadla",
    "hectare",
    "survey",
    "possession",
    "award",
    "notification",
    "acquisition",
    "discrepancy",
    "compensation",
    "landowner",
    "gazette"
]

MAX_AUDIO_DURATION_SECONDS = 30.0
MAX_AUDIO_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _safe_sarvam_error(response: requests.Response) -> dict:
    """Extract only non-sensitive diagnostic fields from a Sarvam error response."""
    try:
        body = response.json()
    except ValueError:
        body = {}

    error = body.get("error", {}) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        error = {}

    return {
        "status": response.status_code,
        "code": str(error.get("code") or "unknown"),
        "message": str(error.get("message") or "Provider returned an HTTP error."),
        "request_id": error.get("request_id"),
    }


class BaseVoiceProvider(ABC):
    """Abstract provider boundary for Speech-to-Text and Text-to-Speech."""

    @abstractmethod
    def speech_to_text(self, audio_bytes: bytes, filename: str, language: str = "auto") -> STTResponse:
        pass

    @abstractmethod
    def text_to_speech(self, text: str, language: str = "en") -> TTSResponse:
        pass


def _resolve_tts_language(lang: str) -> str:
    """Ensure TTS never receives 'auto' or 'unknown'; resolve to 'en', 'hi', or 'mr'."""
    clean_lang = (lang or "").strip().lower()
    if clean_lang in ["en", "en-in", "english"]:
        return "en"
    elif clean_lang in ["hi", "hi-in", "hindi"]:
        return "hi"
    elif clean_lang in ["mr", "mr-in", "marathi"]:
        return "mr"
    else:
        # Default fallback for unrecognised language is English
        return "en"


def _estimate_audio_duration(audio_bytes: bytes, filename: str) -> float:
    """
    Estimate audio duration in seconds.
    Tries wave module for WAV files; falls back to byte size estimate for compressed audio.
    """
    if not audio_bytes:
        return 0.0

    if filename.lower().endswith(".wav") or audio_bytes[:4] == b'RIFF':
        try:
            import wave
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass

    # Rough heuristic for uncompressed/compressed audio fallback (~32KB/sec for speech)
    return len(audio_bytes) / 32000.0


def _detect_audio_mime_type(audio_bytes: bytes, filename: str) -> tuple:
    """
    Infers MIME type and safe filename extension based on magic bytes and filename.
    Returns (mime_type, safe_filename)
    """
    fn = filename or "recording.wav"
    ext = os.path.splitext(fn)[1].lower()

    if audio_bytes.startswith(b'\x1a\x45\xdf\xa3'):
        # WebM format (standard for Streamlit st.audio_input in Chrome/Firefox/Safari)
        return "audio/webm", (fn if ext in [".webm"] else f"{os.path.splitext(fn)[0]}.webm")
    elif audio_bytes.startswith(b'OggS'):
        return "audio/ogg", (fn if ext in [".ogg", ".opus"] else f"{os.path.splitext(fn)[0]}.ogg")
    elif audio_bytes.startswith(b'RIFF'):
        return "audio/wav", (fn if ext in [".wav"] else f"{os.path.splitext(fn)[0]}.wav")
    elif audio_bytes.startswith(b'ID3') or audio_bytes[:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2']:
        return "audio/mpeg", (fn if ext in [".mp3"] else f"{os.path.splitext(fn)[0]}.mp3")
    elif len(audio_bytes) >= 8 and audio_bytes[4:8] == b'ftyp':
        return "audio/m4a", (fn if ext in [".m4a", ".mp4"] else f"{os.path.splitext(fn)[0]}.m4a")

    # Extension fallback
    if ext == ".webm":
        return "audio/webm", fn
    elif ext in [".mp3", ".mpeg"]:
        return "audio/mpeg", fn
    elif ext in [".m4a", ".mp4"]:
        return "audio/m4a", fn
    elif ext in [".ogg", ".opus"]:
        return "audio/ogg", fn
    elif ext == ".wav":
        return "audio/wav", fn
    else:
        return "audio/wav", fn


class SarvamVoiceProvider(BaseVoiceProvider):
    """
    Production Sarvam AI Provider implementation using official REST API endpoints.
    - Speech-to-Text: https://api.sarvam.ai/speech-to-text
    - Text-to-Speech: https://api.sarvam.ai/text-to-speech
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not found in environment.")

    def speech_to_text(self, audio_bytes: bytes, filename: str, language: str = "auto") -> STTResponse:
        if not audio_bytes:
            return STTResponse(
                transcript="",
                language="unknown",
                provider="sarvam",
                duration_seconds=0.0,
                message="Empty audio payload provided."
            )

        if len(audio_bytes) > MAX_AUDIO_FILE_SIZE_BYTES:
            raise ValueError(f"Audio file size exceeds maximum limit of {MAX_AUDIO_FILE_SIZE_BYTES // (1024*1024)}MB.")

        duration = _estimate_audio_duration(audio_bytes, filename)
        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration ({duration:.1f}s) exceeds maximum MVP limit of 30 seconds.")

        # Map language codes: 'auto' -> 'unknown'
        lang_clean = (language or "auto").strip().lower()
        if lang_clean == "auto":
            sarvam_lang_code = "unknown"
        elif lang_clean in ["hi", "hi-in"]:
            sarvam_lang_code = "hi-IN"
        elif lang_clean in ["mr", "mr-in"]:
            sarvam_lang_code = "mr-IN"
        elif lang_clean in ["en", "en-in"]:
            sarvam_lang_code = "en-IN"
        else:
            sarvam_lang_code = "unknown"

        mime_type, safe_filename = _detect_audio_mime_type(audio_bytes, filename)

        # Safe diagnostic logging (NO SECRETS)
        model = "saaras:v4"
        mode = None  # Sarvam supports mode only with saaras:v3; omit it for v4.
        keyterms = json.dumps(LAND_DOMAIN_KEYTERMS)

        logger.info(
            "Sarvam STT Dispatch: file_present=%s, byte_length=%d, filename='%s', "
            "mime_type='%s', language_code='%s', model='%s', mode='%s', "
            "keyterms_present=%s, keyterm_count=%d",
            bool(audio_bytes),
            len(audio_bytes),
            safe_filename,
            mime_type,
            sarvam_lang_code,
            model,
            "omitted (v4)" if mode is None else mode,
            bool(LAND_DOMAIN_KEYTERMS),
            len(LAND_DOMAIN_KEYTERMS),
        )

        url = "https://api.sarvam.ai/speech-to-text"
        headers = {
            "api-subscription-key": self.api_key
        }

        # Form data payload
        files = {
            "file": (safe_filename, audio_bytes, mime_type)
        }
        data = {
            "model": model,
            "language_code": sarvam_lang_code,
            "keyterms": keyterms,
        }

        try:
            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)

            if response.status_code >= 400:
                error = _safe_sarvam_error(response)
                logger.error(
                    "Sarvam STT HTTP error: status=%s, code='%s', message='%s', request_id='%s'",
                    error["status"],
                    error["code"],
                    error["message"],
                    error["request_id"] or "none",
                )
                raise RuntimeError(
                    "Sarvam STT HTTP error: "
                    f"status={error['status']}, code={error['code']}, "
                    f"message={error['message']}, request_id={error['request_id'] or 'none'}"
                )

            res_json = response.json()

            raw_transcript = res_json.get("transcript", "")
            ret_lang_code = res_json.get("language_code", "")

            # Normalize returned language code
            detected_lang = "unknown"
            if ret_lang_code:
                if "hi" in ret_lang_code.lower():
                    detected_lang = "hi"
                elif "mr" in ret_lang_code.lower():
                    detected_lang = "mr"
                elif "en" in ret_lang_code.lower():
                    detected_lang = "en"

            if detected_lang == "unknown" and lang_clean != "auto":
                detected_lang = lang_clean

            return STTResponse(
                transcript=raw_transcript,
                language=detected_lang,
                provider="sarvam",
                duration_seconds=round(duration, 2),
                message="STT transcription successful."
            )
        except Exception as e:
            logger.error(f"Sarvam STT request failed: {e}")
            raise RuntimeError(f"Sarvam STT failed: {str(e)}")


    def text_to_speech(self, text: str, language: str = "en") -> TTSResponse:
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is missing.")

        if not text or not text.strip():
            raise ValueError("TTS text input cannot be empty.")

        # Ensure TTS never receives 'auto' or 'unknown'
        target_lang = _resolve_tts_language(language)

        lang_code_map = {
            "en": "en-IN",
            "hi": "hi-IN",
            "mr": "mr-IN"
        }
        sarvam_lang_code = lang_code_map.get(target_lang, "en-IN")

        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "target_language_code": sarvam_lang_code,
            "speaker": "shubh",
            "pace": 1.0,
            "speech_sample_rate": 24000,
            "model": "bulbul:v3",
            "output_audio_codec": "wav"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code >= 400:
                error = _safe_sarvam_error(response)
                logger.error(
                    "Sarvam TTS HTTP error: status=%s, code='%s', message='%s', request_id='%s'",
                    error["status"],
                    error["code"],
                    error["message"],
                    error["request_id"] or "none",
                )
                raise RuntimeError(
                    "Sarvam TTS HTTP error: "
                    f"status={error['status']}, code={error['code']}, "
                    f"message={error['message']}, request_id={error['request_id'] or 'none'}"
                )

            res_json = response.json()

            audios = res_json.get("audios", [])
            audio_b64 = audios[0].strip() if audios and isinstance(audios[0], str) else None

            if not audio_b64:
                raise RuntimeError("Sarvam TTS returned empty audio payload.")
            try:
                if not base64.b64decode(audio_b64, validate=True):
                    raise ValueError("decoded audio is empty")
            except (binascii.Error, ValueError, TypeError) as e:
                raise RuntimeError(f"Sarvam TTS returned invalid audio payload: {e}") from e

            return TTSResponse(
                audio_base64=audio_b64,
                language=target_lang,
                provider="sarvam",
                format="wav",
                message="TTS synthesis successful."
            )
        except Exception as e:
            logger.error(f"Sarvam TTS request failed: {e}")
            raise RuntimeError(f"Sarvam TTS failed: {str(e)}")


class MockVoiceProvider(BaseVoiceProvider):
    """
    Mock Voice Provider for automated testing and offline fallback.
    Simulates Sarvam STT and TTS without requiring network calls or secret API keys.
    """

    def __init__(self):
        self._mock_transcripts = {
            "en": "What is the compensation for Survey 142/3A in Vadadala?",
            "hi": "इस भूमि का मुआवजा कितना स्वीकृत हुआ है?",
            "mr": "या जमिनीची भरपाई किती घोषित झाली आहे?"
        }

    def speech_to_text(self, audio_bytes: bytes, filename: str, language: str = "auto") -> STTResponse:
        if not audio_bytes:
            return STTResponse(
                transcript="",
                language="unknown",
                provider="mock_sarvam",
                duration_seconds=0.0,
                message="Empty audio payload provided."
            )

        if len(audio_bytes) > MAX_AUDIO_FILE_SIZE_BYTES:
            raise ValueError(f"Audio file size exceeds maximum limit of {MAX_AUDIO_FILE_SIZE_BYTES // (1024*1024)}MB.")

        duration = _estimate_audio_duration(audio_bytes, filename)
        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration ({duration:.1f}s) exceeds maximum MVP limit of 30 seconds.")


        lang_clean = (language or "auto").strip().lower()
        resolved_lang = "en" if lang_clean in ["auto", "unknown"] else _resolve_tts_language(lang_clean)

        transcript = self._mock_transcripts.get(resolved_lang, self._mock_transcripts["en"])

        return STTResponse(
            transcript=transcript,
            language=resolved_lang,
            provider="mock_sarvam",
            duration_seconds=round(duration, 2),
            message="Mock STT transcription successful."
        )

    def text_to_speech(self, text: str, language: str = "en") -> TTSResponse:
        if not text or not text.strip():
            raise ValueError("TTS text input cannot be empty.")

        target_lang = _resolve_tts_language(language)

        # Generate lightweight 0.5s dummy WAV header + silence byte payload as base64
        dummy_wav = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        audio_b64 = base64.b64encode(dummy_wav).decode('utf-8')

        return TTSResponse(
            audio_base64=audio_b64,
            language=target_lang,
            provider="mock_sarvam",
            format="wav",
            message="Mock TTS synthesis successful."
        )


class VoiceService:
    """
    Unified Fault-Tolerant Voice Service Adapter.
    Delegates to SarvamVoiceProvider or MockVoiceProvider.
    Ensures STT and TTS errors do not break core text RAG APIs.
    """

    def __init__(self, provider: Optional[BaseVoiceProvider] = None):
        if provider:
            self.provider = provider
        else:
            api_key = os.getenv("SARVAM_API_KEY")
            if api_key and len(api_key.strip()) > 5:
                self.provider = SarvamVoiceProvider(api_key=api_key)
            else:
                self.provider = MockVoiceProvider()

    def transcribe(self, audio_bytes: bytes, filename: str, language: str = "auto") -> STTResponse:
        try:
            return self.provider.speech_to_text(audio_bytes=audio_bytes, filename=filename, language=language)
        except Exception as e:
            logger.warning(f"STT transcription failed: {e}")
            return STTResponse(
                transcript="",
                language="unknown",
                provider="failed",
                message=f"STT Error: {str(e)}"
            )

    def synthesize(self, text: str, language: str = "en") -> TTSResponse:
        # Guarantee language is resolved prior to synthesis
        resolved_lang = _resolve_tts_language(language)
        try:
            return self.provider.text_to_speech(text=text, language=resolved_lang)
        except Exception as e:
            logger.warning(f"TTS synthesis failed: {e}")
            return TTSResponse(
                audio_base64=None,
                language=resolved_lang,
                provider="failed",
                format="wav",
                message=f"TTS Error: {str(e)}"
            )
