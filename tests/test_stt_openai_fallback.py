"""Tests for OpenAI Whisper STT fallback after Gemini failures."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services import stt_service


class SttWrapperTimeoutTests(unittest.TestCase):
    def test_exam_modes_use_longer_wrapper(self) -> None:
        self.assertEqual(stt_service.stt_wrapper_timeout_sec("mini_mock_v2"), 50)
        self.assertEqual(stt_service.stt_wrapper_timeout_sec("mock_v2"), 50)
        self.assertEqual(stt_service.stt_wrapper_timeout_sec("mini_mock"), 50)

    def test_topic_practice_uses_default_wrapper(self) -> None:
        self.assertEqual(stt_service.stt_wrapper_timeout_sec("topic_practice_v2"), 25)
        self.assertEqual(stt_service.stt_wrapper_timeout_sec(""), 25)


class SttOpenAiHelperTests(unittest.TestCase):
    def test_filename_ext_for_mime(self) -> None:
        self.assertEqual(stt_service._filename_ext_for_mime("audio/webm"), "webm")
        self.assertEqual(stt_service._filename_ext_for_mime("audio/wav; codecs=1"), "wav")
        self.assertEqual(stt_service._filename_ext_for_mime("audio/unknown"), "webm")

    def test_whisper_language_code(self) -> None:
        self.assertEqual(stt_service._whisper_language_code("en-US"), "en")
        self.assertEqual(stt_service._whisper_language_code("ko_KR"), "ko")
        self.assertIsNone(stt_service._whisper_language_code("english"))


class SttOpenAiFallbackTests(unittest.TestCase):
    _AUDIO = b"\x00" * 2048

    @patch("services.stt_service._invoke_openai_stt_model")
    @patch("services.stt_service._invoke_stt_model")
    @patch("services.stt_service.build_stt_model_candidates")
    @patch("services.stt_service.get_gemini_api_key", create=True)
    def test_gemini_failure_falls_back_to_openai(
        self,
        get_gemini_key_mock: MagicMock,
        models_mock: MagicMock,
        invoke_gemini_mock: MagicMock,
        invoke_openai_mock: MagicMock,
    ) -> None:
        get_gemini_key_mock.return_value = "gemini-key"
        models_mock.return_value = ["gemini-stt-model"]
        invoke_gemini_mock.return_value = (None, "api_error", "503 overload")
        invoke_openai_mock.return_value = ("I enjoy listening to music on weekends.", "", "")

        result = stt_service._transcribe_answer_audio_impl(
            self._AUDIO,
            mime_type="audio/webm",
            language_hint="en-US",
            question_text="What do you do in your free time?",
            mode="topic_v2",
            question_id="q1",
            api_key="gemini-key",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["model_used"], stt_service.OPENAI_STT_MODEL)
        self.assertIn("music", result["transcript"].lower())
        invoke_openai_mock.assert_called_once()

    @patch("services.stt_service._invoke_openai_stt_model")
    @patch("services.stt_service._invoke_stt_model")
    @patch("services.stt_service.build_stt_model_candidates")
    def test_gemini_failure_without_openai_key_returns_failure(
        self,
        models_mock: MagicMock,
        invoke_gemini_mock: MagicMock,
        invoke_openai_mock: MagicMock,
    ) -> None:
        models_mock.return_value = ["gemini-stt-model"]
        invoke_gemini_mock.return_value = (None, "api_error", "503 overload")
        invoke_openai_mock.return_value = (None, "openai_skipped", "openai_api_key_not_configured")

        result = stt_service._transcribe_answer_audio_impl(
            self._AUDIO,
            mime_type="audio/webm",
            language_hint="en-US",
            question_text="What do you do in your free time?",
            mode="topic_v2",
            question_id="q1",
            api_key="gemini-key",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error_category"], "api_error")
        invoke_openai_mock.assert_called_once()

    @patch("services.stt_service._invoke_openai_stt_model")
    @patch("services.stt_service.build_stt_model_candidates")
    def test_no_gemini_key_uses_openai_only(
        self,
        models_mock: MagicMock,
        invoke_openai_mock: MagicMock,
    ) -> None:
        models_mock.return_value = []
        invoke_openai_mock.return_value = ("My favorite hobby is reading books.", "", "")

        with patch("utils.secrets.get_gemini_api_key", return_value=None):
            result = stt_service._transcribe_answer_audio_impl(
                self._AUDIO,
                mime_type="audio/webm",
                language_hint="en-US",
                question_text="Tell me about your hobby.",
                mode="topic_v2",
                question_id="q2",
                api_key=None,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "openai")
        invoke_openai_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
