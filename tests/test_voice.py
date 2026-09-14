import io
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.voice_service import (
    VoiceService,
    MockVoiceProvider,
    SarvamVoiceProvider,
    _resolve_tts_language,
    LAND_DOMAIN_KEYTERMS,
    MAX_AUDIO_DURATION_SECONDS
)
from backend.core import dependencies


class TestVoiceSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Generate lightweight 0.5s dummy WAV bytes
        cls.dummy_audio = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'

    def setUp(self):
        # Force mock provider for predictable unit test behavior
        self.mock_service = VoiceService(provider=MockVoiceProvider())
        dependencies._voice_service = self.mock_service

    def test_01_english_stt(self):
        """1. English STT: Transcribes audio with language='en'."""
        files = {"file": ("test_en.wav", self.dummy_audio, "audio/wav")}
        data = {"language": "en"}
        response = self.client.post("/voice/transcribe", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "en")
        self.assertIn("compensation", res["transcript"].lower())

    def test_02_hindi_stt(self):
        """2. Hindi STT: Transcribes audio with language='hi'."""
        files = {"file": ("test_hi.wav", self.dummy_audio, "audio/wav")}
        data = {"language": "hi"}
        response = self.client.post("/voice/transcribe", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "hi")
        self.assertIn("मुआवजा", res["transcript"])

    def test_03_marathi_stt(self):
        """3. Marathi STT: Transcribes audio with language='mr'."""
        files = {"file": ("test_mr.wav", self.dummy_audio, "audio/wav")}
        data = {"language": "mr"}
        response = self.client.post("/voice/transcribe", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "mr")
        self.assertIn("भरपाई", res["transcript"])

    def test_04_auto_language_identification(self):
        """4. Auto Language Identification: Maps 'auto' to resolved language or 'unknown' for Sarvam."""
        files = {"file": ("test_auto.wav", self.dummy_audio, "audio/wav")}
        data = {"language": "auto"}
        response = self.client.post("/voice/transcribe", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn(res["language"], ["en", "hi", "mr", "unknown"])

    def test_05_english_tts(self):
        """5. English TTS: Synthesizes text into audio with language='en'."""
        payload = {"text": "The total compensation for parcel 142/3A is Rs 2,450,000.", "language": "en"}
        response = self.client.post("/voice/synthesize", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "en")
        self.assertIsNotNone(res["audio_base64"])

    def test_06_hindi_tts(self):
        """6. Hindi TTS: Synthesizes text into audio with language='hi'."""
        payload = {"text": "सर्वे 142/3A का कुल मुआवजा ₹2,450,000 स्वीकृत है।", "language": "hi"}
        response = self.client.post("/voice/synthesize", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "hi")
        self.assertIsNotNone(res["audio_base64"])

    def test_07_marathi_tts(self):
        """7. Marathi TTS: Synthesizes text into audio with language='mr'."""
        payload = {"text": "सर्व्हे १४२/३अ चा एकूण मोबदला ₹२४,५०,००० आहे.", "language": "mr"}
        response = self.client.post("/voice/synthesize", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["language"], "mr")
        self.assertIsNotNone(res["audio_base64"])

    def test_08_stt_failure_handling(self):
        """8. STT Failure Handling: Graceful error status when transcription fails."""
        mock_failing_provider = MagicMock()
        mock_failing_provider.speech_to_text.side_effect = RuntimeError("STT Provider Connection Timeout")
        dependencies._voice_service = VoiceService(provider=mock_failing_provider)

        files = {"file": ("corrupt.wav", b"INVALID_BYTES", "audio/wav")}
        response = self.client.post("/voice/transcribe", files=files)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["provider"], "failed")
        self.assertEqual(res["transcript"], "")

    def test_09_tts_failure_graceful_degradation(self):
        """9. TTS Failure Graceful Degradation: /voice/ask still returns text answer when TTS fails."""
        mock_failing_tts_provider = MagicMock()
        mock_failing_tts_provider.speech_to_text.return_value = self.mock_service.transcribe(self.dummy_audio, "query.wav", "en")
        mock_failing_tts_provider.text_to_speech.side_effect = RuntimeError("TTS Service Outage")
        dependencies._voice_service = VoiceService(provider=mock_failing_tts_provider)

        files = {"file": ("query.wav", self.dummy_audio, "audio/wav")}
        data = {"project_id": "PRJ-NHAI-2024"}
        response = self.client.post("/voice/ask", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("answer", res)
        self.assertFalse(res["audio_available"])
        self.assertIsNone(res["audio_base64"])

    def test_10_sarvam_service_outage_simulation(self):
        """10. Sarvam Service Outage Simulation: Falls back gracefully to mock/failure response."""
        provider = SarvamVoiceProvider(api_key="mock_invalid_key_12345")
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Sarvam Server 503 Unavailable")
            service = VoiceService(provider=provider)
            stt_res = service.transcribe(self.dummy_audio, "test.wav", "en")
            self.assertEqual(stt_res.provider, "failed")

    def test_11_voice_ask_grounded_answer_preservation(self):
        """11. /voice/ask Grounded Answer Preservation: Preserves grounded text answer from RAG engine."""
        files = {"file": ("query.wav", self.dummy_audio, "audio/wav")}
        data = {"project_id": "PRJ-NHAI-2024", "language": "en"}
        response = self.client.post("/voice/ask", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("transcript", res)
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 5)

    def test_12_citation_preservation(self):
        """12. Citation Preservation: Preserves document source citations in /voice/ask."""
        files = {"file": ("query.wav", self.dummy_audio, "audio/wav")}
        data = {"project_id": "PRJ-NHAI-2024"}
        response = self.client.post("/voice/ask", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("citations", res)

    def test_13_evidence_coverage_preservation(self):
        """13. Evidence Coverage Preservation: Preserves COMPLETE / PARTIAL / INSUFFICIENT coverage badge."""
        files = {"file": ("query.wav", self.dummy_audio, "audio/wav")}
        data = {"project_id": "PRJ-NHAI-2024"}
        response = self.client.post("/voice/ask", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn(res["evidence_coverage"], ["COMPLETE", "PARTIAL", "INSUFFICIENT"])

    def test_14_conflict_preservation(self):
        """14. Conflict Preservation: Preserves database vs document conflicts in /voice/ask."""
        files = {"file": ("query.wav", self.dummy_audio, "audio/wav")}
        data = {"project_id": "PRJ-NHAI-2024", "parcel_id": "PCL-VADADALA-142-3A"}
        response = self.client.post("/voice/ask", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("conflicts", res)

    def test_15_existing_ask_unaffected(self):
        """15. Existing /ask Unaffected: Existing /ask text contract remains 100% operational."""
        payload = {"query": "What is the compensation for Survey 142/3A?", "project_id": "PRJ-NHAI-2024"}
        response = self.client.post("/ask", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("answer", res)
        self.assertIn("citations", res)

    def test_16_secret_api_key_protection(self):
        """16. Secret API Key Protection: Verifies SARVAM_API_KEY never leaks in responses or exceptions."""
        provider = SarvamVoiceProvider(api_key="secret_test_key_xyz987654321")
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Sarvam HTTP 401 Unauthorized Secret Key Failure")
            service = VoiceService(provider=provider)
            res = service.transcribe(self.dummy_audio, "test.wav", "en")
            # Verify response string does not expose key
            self.assertNotIn("secret_test_key_xyz987654321", res.model_dump_json())

    def test_17_invalid_audio_format_rejection(self):
        """17. Invalid Audio Format Rejection: Empty or malformed audio handles cleanly."""
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = self.client.post("/voice/transcribe", files=files)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(res["transcript"], "")

    def test_18_unsupported_language_rejection(self):
        """18. Unsupported Language Rejection: Unknown language code falls back safely to 'en'."""
        resolved = _resolve_tts_language("unsupported_lang_code_123")
        self.assertEqual(resolved, "en")

    def test_19_audio_duration_limit_enforcement(self):
        """19. Audio Duration Limit Enforcement: Rejects audio exceeding maximum MVP 30s limit."""
        large_audio = b"0" * (32000 * 35)  # ~35 seconds
        provider = MockVoiceProvider()
        with self.assertRaises(ValueError) as ctx:
            provider.speech_to_text(large_audio, "long.mp3", "en")
        self.assertIn("exceeds maximum MVP limit of 30 seconds", str(ctx.exception))

    def test_20_controlled_keyterm_allowlist_safety(self):
        """20. Controlled Keyterm Allowlist Safety: Keyterm list contains only land-domain terms."""
        for term in LAND_DOMAIN_KEYTERMS:
            self.assertIsInstance(term, str)
            self.assertNotIn("api", term.lower())
            self.assertNotIn("key", term.lower())
            self.assertNotIn("secret", term.lower())

    def test_21_tts_auto_language_resolution(self):
        """21. TTS Auto-Language Resolution: Verifies TTS never receives 'auto' or 'unknown'."""
        self.assertEqual(_resolve_tts_language("auto"), "en")
        self.assertEqual(_resolve_tts_language("unknown"), "en")
        self.assertEqual(_resolve_tts_language("hi-IN"), "hi")
        self.assertEqual(_resolve_tts_language("mr-IN"), "mr")


if __name__ == "__main__":
    unittest.main()
