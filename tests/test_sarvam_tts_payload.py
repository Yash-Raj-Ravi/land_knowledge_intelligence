import base64
import unittest
from unittest.mock import Mock, patch

from backend.services.voice_service import SarvamVoiceProvider, VoiceService


class TestSarvamTTSPayload(unittest.TestCase):
    def test_bulbul_v3_payload_and_audio(self):
        wav_base64 = base64.b64encode(b"RIFFfake-wav").decode("ascii")
        response = Mock(status_code=200)
        response.json.return_value = {"audios": [wav_base64]}

        with patch("backend.services.voice_service.requests.post", return_value=response) as post:
            result = SarvamVoiceProvider(api_key="test-key").text_to_speech(
                "हिंदी उत्तर", "hi"
            )

        payload = post.call_args.kwargs["json"]
        self.assertEqual(post.call_args.args[0], "https://api.sarvam.ai/text-to-speech")
        self.assertEqual(payload, {
            "text": "हिंदी उत्तर",
            "target_language_code": "hi-IN",
            "speaker": "shubh",
            "pace": 1.0,
            "speech_sample_rate": 24000,
            "model": "bulbul:v3",
            "output_audio_codec": "wav",
        })
        self.assertEqual(result.audio_base64, wav_base64)
        self.assertTrue(base64.b64decode(result.audio_base64))

    def test_http_error_is_safe_and_structured(self):
        response = Mock(status_code=400)
        response.json.return_value = {
            "error": {
                "code": "invalid_request_error",
                "message": "invalid TTS request",
                "request_id": "req_test_123",
                "secret": "must-not-be-returned",
            }
        }

        with patch("backend.services.voice_service.requests.post", return_value=response):
            result = VoiceService(
                provider=SarvamVoiceProvider(api_key="secret_test_key")
            ).synthesize("answer", "en")

        self.assertEqual(result.provider, "failed")
        self.assertIn("status=400", result.message)
        self.assertIn("code=invalid_request_error", result.message)
        self.assertIn("message=invalid TTS request", result.message)
        self.assertIn("request_id=req_test_123", result.message)
        self.assertNotIn("secret_test_key", result.model_dump_json())
        self.assertNotIn("must-not-be-returned", result.model_dump_json())
        self.assertIsNone(result.audio_base64)


if __name__ == "__main__":
    unittest.main()
