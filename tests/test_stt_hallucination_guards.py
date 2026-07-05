"""Tests for STT short-audio guards and hallucination rejection."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services import stt_service


class SttPreGuardTests(unittest.TestCase):
    def test_too_short_by_bytes_skips_api(self) -> None:
        result = stt_service._transcribe_answer_audio_impl(
            b"\x00" * 5000,
            mime_type="audio/webm",
            language_hint="en",
            question_text="Tell me about your hobby.",
            mode="topic_practice_v2",
            question_id="q1",
            api_key="key",
            duration_seconds=60.0,
        )
        self.assertTrue(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("error_category"), "audio_too_short")
        self.assertEqual(result.get("transcript"), "")
        self.assertEqual(stt_service.derive_stt_status(result), "insufficient_response")

    def test_too_short_by_duration_skips_api(self) -> None:
        result = stt_service._transcribe_answer_audio_impl(
            b"\x00" * 20_000,
            mime_type="audio/webm",
            language_hint="en",
            question_text="Tell me about your hobby.",
            mode="topic_practice_v2",
            question_id="q1",
            api_key="key",
            duration_seconds=1.0,
        )
        self.assertTrue(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("error_category"), "audio_too_short")
        self.assertEqual(result.get("transcript"), "")

    def test_normal_duration_and_bytes_passes_pre_guard_to_api(self) -> None:
        with patch.object(stt_service, "build_stt_model_candidates", return_value=[]):
            with patch.object(stt_service, "_run_openai_stt_fallback", return_value=None) as fb:
                with patch("utils.secrets.get_gemini_api_key", return_value=None):
                    stt_service._transcribe_answer_audio_impl(
                        b"\x00" * 20_000,
                        mime_type="audio/webm",
                        language_hint="en",
                        question_text="Tell me about your hobby.",
                        mode="topic_practice_v2",
                        question_id="q1",
                        api_key=None,
                        duration_seconds=45.0,
                    )
        fb.assert_called_once()


def _diverse_words(n: int) -> str:
    """Build n distinct letter-only tokens (regex-safe for count_english_words)."""
    parts: list[str] = []
    for i in range(n):
        a = chr(ord("a") + i % 26)
        b = chr(ord("a") + (i // 26) % 26)
        c = chr(ord("a") + (i // 676) % 26)
        parts.append(f"{a}{b}{c}")
    return " ".join(parts)


class SttHallucinationDetectionTests(unittest.TestCase):
    def test_words_per_second_rejects_implausible_rate(self) -> None:
        long_text = _diverse_words(30)
        is_hallu, reason = stt_service.looks_like_stt_hallucination(
            long_text,
            duration_seconds=1.0,
        )
        self.assertTrue(is_hallu)
        self.assertEqual(reason, "words_per_second")

    def test_production_case_webm_duration_not_rejected(self) -> None:
        """91 words @ ~570KB webm — old 32KB/s gave 17.8s/5.1wps false reject."""
        from services.evaluation.eval_audio import compute_audio_duration_seconds

        audio_len = int(17.8 * 32_000)  # production-like byte size
        blob = b"\x1a\x45\xdf\xa3" + (b"\x00" * (audio_len - 4))
        dur, method = compute_audio_duration_seconds(blob, "audio/webm")
        self.assertEqual(method, "fallback_bytes")
        self.assertGreater(dur, 40.0)
        text = _diverse_words(91)
        is_hallu, reason = stt_service.looks_like_stt_hallucination(
            text,
            duration_seconds=dur,
        )
        self.assertFalse(is_hallu, f"unexpected reject reason={reason} dur={dur}")

    def test_wps_limit_env_override(self) -> None:
        with patch.dict("os.environ", {"STT_WPS_LIMIT": "10"}):
            self.assertEqual(stt_service._max_plausible_words_per_sec(), 10.0)

    def test_short_audio_long_transcript_rejected(self) -> None:
        text = _diverse_words(20)
        is_hallu, reason = stt_service.looks_like_stt_hallucination(
            text,
            duration_seconds=2.0,
        )
        self.assertTrue(is_hallu)
        self.assertIn(
            reason,
            ("words_per_second", "short_audio_long_transcript"),
        )

    def test_normal_answer_not_rejected(self) -> None:
        text = _diverse_words(80)
        is_hallu, _ = stt_service.looks_like_stt_hallucination(
            text,
            duration_seconds=60.0,
        )
        self.assertFalse(is_hallu)

    def test_build_success_rejects_high_wps_transcript(self) -> None:
        raw = _diverse_words(30)
        result = stt_service._build_stt_success_from_raw(
            raw,
            model_used="gemini-test",
            provider="gemini",
            attempts=1,
            elapsed=0.5,
            audio_len=20_000,
            duration_seconds=1.0,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("error_category"), "hallucination_rejected")
        self.assertEqual(result.get("transcript"), "")
        self.assertEqual(stt_service.derive_stt_status(result), "insufficient_response")

    def test_build_success_accepts_normal_speech_metrics(self) -> None:
        raw = _diverse_words(80)
        result = stt_service._build_stt_success_from_raw(
            raw,
            model_used="gemini-test",
            provider="gemini",
            attempts=1,
            elapsed=0.5,
            audio_len=80_000,
            duration_seconds=60.0,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("word_count"), 80)
        self.assertEqual(stt_service.derive_stt_status(result), "transcript_ready")

    @patch("services.stt_service._invoke_openai_stt_model")
    def test_wps_guard_whisper_overrule_accepts(self, mock_whisper: MagicMock) -> None:
        gemini_text = _diverse_words(91)
        whisper_text = _diverse_words(80)
        mock_whisper.return_value = (whisper_text, "", "")
        blob = b"\x1a\x45\xdf\xa3" + (b"\x00" * (int(17.8 * 32_000) - 4))
        # Force WPS trip at 6.5 limit even if byte sniff would be longer.
        result = stt_service._build_stt_success_from_raw(
            gemini_text,
            model_used="gemini-test",
            provider="gemini",
            attempts=1,
            elapsed=0.5,
            audio_len=len(blob),
            duration_seconds=10.0,
            audio_bytes=blob,
            mime_type="audio/webm",
            language_hint="en",
            question_text="Tell me about your hobby.",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("word_count"), 91)
        mock_whisper.assert_called_once()

    @patch("services.stt_service._invoke_openai_stt_model")
    def test_wps_guard_whisper_short_confirms_rejection(self, mock_whisper: MagicMock) -> None:
        gemini_text = _diverse_words(30)
        mock_whisper.return_value = ("hello", "", "")
        result = stt_service._build_stt_success_from_raw(
            gemini_text,
            model_used="gemini-test",
            provider="gemini",
            attempts=1,
            elapsed=0.5,
            audio_len=20_000,
            duration_seconds=1.0,
            audio_bytes=b"\x00" * 20_000,
            mime_type="audio/webm",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.get("rejected_as_no_speech"))
        self.assertEqual(result.get("error_category"), "hallucination_rejected")


class SttWhisperPromptTests(unittest.TestCase):
    @patch("services.gemini_json_client.classify_openai_exception")
    @patch("utils.secrets.get_openai_api_key", return_value="sk-test")
    def test_short_audio_omits_whisper_question_prompt(self, _key: MagicMock, _cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = "hello world"
        with patch("openai.OpenAI", return_value=mock_client):
            stt_service._invoke_openai_stt_model(
                audio_bytes=b"\x00" * 20_000,
                mime_type="audio/webm",
                language_hint="en",
                question_text="What is your favorite movie and why do you like it?",
                duration_seconds=2.0,
            )
        kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        self.assertNotIn("prompt", kwargs)

    @patch("services.gemini_json_client.classify_openai_exception")
    @patch("utils.secrets.get_openai_api_key", return_value="sk-test")
    def test_longer_audio_may_include_whisper_prompt(self, _key: MagicMock, _cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = "hello world"
        with patch("openai.OpenAI", return_value=mock_client):
            stt_service._invoke_openai_stt_model(
                audio_bytes=b"\x00" * 20_000,
                mime_type="audio/webm",
                language_hint="en",
                question_text="What is your favorite movie?",
                duration_seconds=5.0,
            )
        kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        self.assertEqual(kwargs.get("prompt"), "What is your favorite movie?")


if __name__ == "__main__":
    unittest.main()
