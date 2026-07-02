"""Tests for STT transcript whitespace normalization."""

from __future__ import annotations

import unittest

from components.exam_saved_screen import build_saved_transcript_html
from services import stt_service


class FlattenTranscriptWhitespaceTests(unittest.TestCase):
    def test_numbered_multiline_becomes_single_line(self) -> None:
        raw = "1. Firstly, I go to work.\n2. Secondly, I have lunch."
        expected = "1. Firstly, I go to work. 2. Secondly, I have lunch."
        self.assertEqual(stt_service._flatten_transcript_whitespace(raw), expected)

    def test_enumeration_without_numbers(self) -> None:
        raw = "Firstly, I go to work.\nSecondly, I have lunch."
        expected = "Firstly, I go to work. Secondly, I have lunch."
        self.assertEqual(stt_service._flatten_transcript_whitespace(raw), expected)

    def test_crlf_and_repeated_spaces(self) -> None:
        raw = "Hello,\r\nworld.   How   are you?"
        self.assertEqual(
            stt_service._flatten_transcript_whitespace(raw),
            "Hello, world. How are you?",
        )

    def test_punctuation_preserved(self) -> None:
        raw = "I like it.\nIt's great!"
        self.assertEqual(
            stt_service._flatten_transcript_whitespace(raw),
            "I like it. It's great!",
        )

    def test_single_line_unchanged(self) -> None:
        text = "I enjoy listening to music on weekends."
        self.assertEqual(stt_service._flatten_transcript_whitespace(text), text)

    def test_empty_and_whitespace_only(self) -> None:
        self.assertEqual(stt_service._flatten_transcript_whitespace(""), "")
        self.assertEqual(stt_service._flatten_transcript_whitespace("   \n\r\n  "), "")


class NormalizeTranscriptTests(unittest.TestCase):
    def test_no_speech_still_stripped_before_flatten(self) -> None:
        self.assertEqual(stt_service._normalize_transcript("(no speech)"), "")
        self.assertEqual(stt_service._normalize_transcript("(no speech detected)"), "")

    def test_applies_flatten_after_no_speech_checks(self) -> None:
        raw = "1. One.\n2. Two."
        self.assertEqual(stt_service._normalize_transcript(raw), "1. One. 2. Two.")


class BuildSttSuccessFromRawTests(unittest.TestCase):
    def test_transcript_flattened_raw_transcript_preserved(self) -> None:
        raw = "1. Firstly, I go to work.\n2. Secondly, I have lunch."
        result = stt_service._build_stt_success_from_raw(
            raw,
            model_used="gemini-test",
            provider="gemini",
            attempts=1,
            elapsed=1.0,
            audio_len=4096,
            duration_seconds=30.0,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(
            result["transcript"],
            "1. Firstly, I go to work. 2. Secondly, I have lunch.",
        )
        self.assertEqual(result["text"], result["transcript"])
        self.assertEqual(result["raw_transcript"], raw)
        self.assertTrue(result["ok"])


class SavedTranscriptHtmlTests(unittest.TestCase):
    def test_numbered_transcript_not_markdown_list(self) -> None:
        transcript = "1. Firstly, I go to work. 2. Secondly, I have lunch."
        html = build_saved_transcript_html(transcript=transcript, accent="teal")
        self.assertIn("tq-saved-transcript", html)
        self.assertIn("tq-screen-marker", html)
        self.assertIn('width="16"', html)
        self.assertIn('height="16"', html)
        self.assertNotIn("<ol", html.lower())
        self.assertIn("1. Firstly, I go to work. 2. Secondly, I have lunch.", html)


if __name__ == "__main__":
    unittest.main()
