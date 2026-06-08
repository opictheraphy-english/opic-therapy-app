"""Topic Practice V2 → practice_history sync."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import streamlit as st

from views.topic_practice_v2 import (
    _KEY_ANSWERS,
    _KEY_FEEDBACK_BY_Q,
    _KEY_PRACTICE_SIG,
    _maybe_persist_topic_v2_history,
    build_topic_v2_history_payload,
)


class TopicV2HistoryTest(unittest.TestCase):
    def setUp(self) -> None:
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def _seed_three_answers(self, topic: str = "movies_tv") -> None:
        st.session_state[_KEY_PRACTICE_SIG] = "test_sig_abc"
        st.session_state[_KEY_ANSWERS] = [
            {
                "q_index": 0,
                "topic": topic,
                "en": "Q1 text",
                "transcript": "answer one",
                "student_answer": "answer one",
                "opic_type": "Q1",
                "status": "saved",
                "answer_id": "a1",
            },
            {
                "q_index": 1,
                "topic": topic,
                "en": "Q2 text",
                "transcript": "answer two",
                "student_answer": "answer two",
                "opic_type": "Q2",
                "status": "saved",
                "answer_id": "a2",
            },
            {
                "q_index": 2,
                "topic": topic,
                "en": "Q3 text",
                "transcript": "answer three",
                "student_answer": "answer three",
                "opic_type": "Q3",
                "status": "saved",
                "answer_id": "a3",
            },
        ]
        st.session_state[_KEY_FEEDBACK_BY_Q] = {
            0: {"ok": True, "summary": "Good flow on Q1"},
            2: {"ok": True, "summary": "Nice ending"},
        }

    def test_build_payload_shape(self) -> None:
        self._seed_three_answers()
        payload = build_topic_v2_history_payload("movies_tv")
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("report_source"), "topic_practice_v2")
        self.assertEqual(payload.get("topic_id"), "movies_tv")
        self.assertEqual(len(payload.get("results") or []), 3)
        self.assertEqual(payload["results"][0]["transcript"], "answer one")
        self.assertEqual(payload["results"][0]["feedback"], "Good flow on Q1")
        self.assertEqual(payload["results"][1]["feedback"], "")
        self.assertIn("completed_at", payload)

    @patch("utils.history_sync.save_history_record", return_value={"id": "row1"})
    def test_logged_in_saves_once(self, mock_save) -> None:
        self._seed_three_answers()
        st.session_state["user_authenticated"] = True

        _maybe_persist_topic_v2_history("movies_tv")
        _maybe_persist_topic_v2_history("movies_tv")

        self.assertEqual(mock_save.call_count, 1)
        body = mock_save.call_args.kwargs
        self.assertEqual(body["practice_type"], "topic_practice")
        self.assertEqual(body["subtype"], "topic_practice")
        content = body["content"]
        self.assertEqual(content.get("topic_id"), "movies_tv")
        self.assertEqual(len(content.get("results") or []), 3)

    @patch("utils.history_sync.save_history_record", return_value={"id": "row1"})
    def test_guest_skips_save(self, mock_save) -> None:
        self._seed_three_answers()
        st.session_state["user_authenticated"] = False

        _maybe_persist_topic_v2_history("movies_tv")

        mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
