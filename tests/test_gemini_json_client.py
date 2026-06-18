"""Tests for Gemini JSON parse + retry helpers."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

from services.api_retry_policy import (
    gemini_json_retry_delay_sec,
    reset_gemini_json_sleep_budget,
)
from services.gemini_json_client import (
    OPENAI_FALLBACK_MODEL,
    classify_gemini_exception,
    invoke_openai_text_json,
    parse_llm_json_response,
    run_gemini_json_model_chain,
)


class GeminiJsonParseTests(unittest.TestCase):
    def test_parses_code_fence(self) -> None:
        raw = 'Here you go:\n```json\n{"summary": "ok", "strength": "nice"}\n```'
        parsed, err = parse_llm_json_response(raw, log_tag="TEST")
        self.assertEqual(err, "")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["summary"], "ok")

    def test_parses_leading_prose(self) -> None:
        raw = 'Sure! {"answer_level": "IM2", "summary": "good"} Hope this helps.'
        parsed, err = parse_llm_json_response(raw, log_tag="TEST")
        self.assertEqual(err, "")
        assert parsed is not None
        self.assertEqual(parsed["answer_level"], "IM2")

    def test_fixes_trailing_comma(self) -> None:
        raw = '{"items": ["a", "b",], "ok": true,}'
        parsed, err = parse_llm_json_response(raw, log_tag="TEST")
        self.assertEqual(err, "")
        assert parsed is not None
        self.assertEqual(parsed["items"], ["a", "b"])

    def test_classify_server_error(self) -> None:
        class ServerError(Exception):
            status_code = 503

        self.assertEqual(classify_gemini_exception(ServerError("overload")), "api_error")

    def test_classify_429(self) -> None:
        self.assertEqual(classify_gemini_exception(Exception("429 RESOURCE_EXHAUSTED")), "quota_or_rate_limit")


class GeminiJsonRetryTests(unittest.TestCase):
    def test_backoff_within_bounds(self) -> None:
        for idx in (1, 2, 3):
            delay = gemini_json_retry_delay_sec(idx)
            self.assertGreaterEqual(delay, 0.0)
            self.assertLessEqual(delay, 3.0 + 0.3)

    @patch("services.gemini_json_client.time.sleep")
    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_5xx_retries_then_next_model(self, invoke_mock, _sleep) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.side_effect = [
            (None, "api_error"),
            (None, "api_error"),
            (None, "api_error"),
            (None, "api_error"),
            ({"summary": "ok"}, ""),
        ]
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a", "model-b"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertEqual(err, "")
        self.assertEqual(parsed, {"summary": "ok"})
        self.assertGreaterEqual(invoke_mock.call_count, 2)

    @patch("services.gemini_json_client.time.sleep")
    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_json_parse_one_retry_per_model(self, invoke_mock, _sleep) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.side_effect = [
            (None, "json_parse_failed"),
            (None, "json_parse_failed"),
            ({"ok": True}, ""),
        ]
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a", "model-b"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertEqual(parsed, {"ok": True})
        self.assertEqual(err, "")
        self.assertEqual(invoke_mock.call_count, 3)

    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_client_error_skips_to_next_model(self, invoke_mock) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.side_effect = [
            (None, "client_error"),
            ({"ok": True}, ""),
        ]
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a", "model-b"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertEqual(parsed, {"ok": True})
        self.assertEqual(invoke_mock.call_count, 2)


class OpenAiFallbackTests(unittest.TestCase):
    @patch("services.gemini_json_client.get_openai_api_key", return_value=None)
    @patch("services.gemini_json_client.invoke_openai_text_json")
    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_no_openai_key_skips_fallback(self, invoke_mock, openai_mock, _key) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.return_value = (None, "api_error")
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertIsNone(parsed)
        self.assertEqual(err, "api_error")
        openai_mock.assert_not_called()

    @patch("services.gemini_json_client.get_openai_api_key", return_value="sk-test")
    @patch("services.gemini_json_client.time.sleep")
    @patch("services.gemini_json_client.invoke_openai_text_json")
    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_openai_fallback_after_gemini_exhaustion(
        self, invoke_mock, openai_mock, _sleep, _key
    ) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.return_value = (None, "api_error")
        openai_mock.return_value = ({"summary": "from-openai"}, "")
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a", "model-b"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertEqual(err, "")
        self.assertEqual(parsed, {"summary": "from-openai"})
        openai_mock.assert_called_once()
        call_kwargs = openai_mock.call_args.kwargs
        self.assertEqual(call_kwargs["model"], OPENAI_FALLBACK_MODEL)
        self.assertEqual(call_kwargs["prompt"], "p")

    @patch("services.gemini_json_client.get_openai_api_key", return_value="sk-test")
    def test_invoke_openai_uses_shared_parser(self, _key) -> None:
        message = type("Msg", (), {"content": '```json\n{"ok": true}\n```'})()
        choice = type("Choice", (), {"message": message})()
        response = type("Resp", (), {"choices": [choice]})()
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = response

        with patch.dict(sys.modules, {"openai": mock_openai}):
            parsed, err = invoke_openai_text_json(
                prompt="return json",
                model=OPENAI_FALLBACK_MODEL,
                log_tag="TEST",
            )
        self.assertEqual(err, "")
        self.assertEqual(parsed, {"ok": True})
        create_kwargs = mock_openai.OpenAI.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(create_kwargs.get("max_completion_tokens"), 4096)
        self.assertEqual(create_kwargs.get("reasoning_effort"), "minimal")
        self.assertNotIn("temperature", create_kwargs)

    @patch("services.gemini_json_client.get_openai_api_key", return_value="sk-test")
    @patch("services.gemini_json_client.invoke_openai_text_json")
    @patch("services.gemini_json_client.invoke_gemini_text_json")
    def test_gemini_success_never_calls_openai(self, invoke_mock, openai_mock, _key) -> None:
        reset_gemini_json_sleep_budget()
        invoke_mock.return_value = ({"summary": "gemini"}, "")
        parsed, err = run_gemini_json_model_chain(
            api_key="k",
            prompt="p",
            models=["model-a"],
            temperature=0.2,
            max_output_tokens=128,
            timeout_ms=1000,
            log_tag="TEST",
        )
        self.assertEqual(parsed, {"summary": "gemini"})
        self.assertEqual(err, "")
        openai_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
