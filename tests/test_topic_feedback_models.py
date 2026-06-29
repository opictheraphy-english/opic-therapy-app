"""Topic V2 feedback model chain defaults."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.evaluation.eval_config import build_topic_feedback_model_candidates


class TopicFeedbackModelTests(unittest.TestCase):
    def test_default_chain_excludes_flash_lite(self) -> None:
        with patch(
            "services.evaluation.eval_config.TOPIC_FEEDBACK_MODEL_NAME",
            "gemini-2.5-flash",
        ):
            models = build_topic_feedback_model_candidates()
        self.assertEqual(models, ["gemini-2.5-flash", "gemini-3.5-flash"])
        self.assertNotIn("gemini-2.5-flash-lite", models)

    def test_env_override_first_model(self) -> None:
        with patch(
            "services.evaluation.eval_config.TOPIC_FEEDBACK_MODEL_NAME",
            "gemini-3.5-flash",
        ):
            models = build_topic_feedback_model_candidates()
        self.assertEqual(models[0], "gemini-3.5-flash")
        self.assertIn("gemini-2.5-flash", models)


if __name__ == "__main__":
    unittest.main()
