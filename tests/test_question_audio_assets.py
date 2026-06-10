"""Tests for static question MP3 lookup helpers."""

from __future__ import annotations

import random
import unittest
from pathlib import Path

from services.mock_exam.mock_exam_test_set_generator import ADVANCED_SET_POOL
from services.mock_v2_question_selector import build_mock_v2_exam
from utils.question_audio_assets import (
    QUESTION_AUDIO_DIR,
    load_question_mp3_bytes,
    mock_v2_question_audio_id,
)

_SURVEY = {
    "leisure": ["영화 보기", "공원 가기"],
    "interests": ["음악 감상하기", "요리하기"],
    "sports": ["농구", "조깅"],
    "travel": ["국내 여행"],
}


class QuestionAudioAssetsTest(unittest.TestCase):
    def test_bank_question_uses_source_id(self) -> None:
        q = {"source_id": "home_q1_001", "combo": "Combo1", "step": "Description"}
        self.assertEqual(mock_v2_question_audio_id(q), "home_q1_001")
        self.assertIsNotNone(load_question_mp3_bytes("home_q1_001"))

    def test_advanced_q14_q15_audio_ids(self) -> None:
        q14 = {
            "combo": "Advanced",
            "step": "Comparison",
            "topic": "phone",
            "source_id": None,
        }
        q15 = {
            "combo": "Advanced",
            "step": "News/Issue",
            "topic": "phone",
            "source_id": None,
        }
        self.assertEqual(mock_v2_question_audio_id(q14), "phone_comparison")
        self.assertEqual(mock_v2_question_audio_id(q15), "phone_news_issue")
        self.assertIsNotNone(load_question_mp3_bytes("phone_comparison"))
        self.assertIsNotNone(load_question_mp3_bytes("phone_news_issue"))

    def test_intro_resolves_to_mock_v2_intro(self) -> None:
        intro = {"combo": "Intro", "step": "Self-Introduction", "source_id": None}
        self.assertEqual(mock_v2_question_audio_id(intro), "mock_v2_intro")

    def test_q5_pool_has_no_audio_id(self) -> None:
        q5 = {
            "combo": "Advanced",
            "step": "질문하기 (Ask the Interviewer)",
            "topic": "Home",
            "source_id": None,
        }
        self.assertEqual(mock_v2_question_audio_id(q5), "")

    def test_ih_al_exam_resolves_audio_ids_for_bank_and_advanced(self) -> None:
        random.seed(3)
        exam = build_mock_v2_exam(_SURVEY, difficulty=5)
        q14, q15 = exam[13], exam[14]
        self.assertEqual(mock_v2_question_audio_id(q14), f"{q14['topic']}_comparison")
        self.assertEqual(mock_v2_question_audio_id(q15), f"{q15['topic']}_news_issue")
        self.assertIsNotNone(load_question_mp3_bytes(mock_v2_question_audio_id(q14)))
        self.assertIsNotNone(load_question_mp3_bytes(mock_v2_question_audio_id(q15)))
        for q in exam[1:10]:
            audio_id = mock_v2_question_audio_id(q)
            self.assertTrue(audio_id)
            self.assertIsNotNone(
                load_question_mp3_bytes(audio_id),
                f"Q{q['question_number']} missing {audio_id}.mp3",
            )
    def test_all_roleplay_mp3_exist(self) -> None:
        from data.opic_question_bank_v2 import (
            get_roleplay_practice_set,
            list_roleplay_set_ids,
        )

        self.assertEqual(len(list_roleplay_set_ids()), 14)
        missing: list[str] = []
        for sid in list_roleplay_set_ids():
            for row in get_roleplay_practice_set(sid):
                qid = str(row.get("id") or "").strip()
                if qid and load_question_mp3_bytes(qid) is None:
                    missing.append(qid)
        self.assertEqual(len(missing), 0, f"missing roleplay mp3: {missing[:5]}")

    def test_ih_al_roleplay_seats_have_mp3(self) -> None:
        random.seed(3)
        exam = build_mock_v2_exam(_SURVEY, difficulty=5)
        for q in exam[10:13]:
            audio_id = mock_v2_question_audio_id(q)
            self.assertTrue(audio_id, f"Q{q['question_number']} missing audio_id")
            self.assertIsNotNone(
                load_question_mp3_bytes(audio_id),
                f"Q{q['question_number']} missing {audio_id}.mp3",
            )

    def test_im_exam_bank_q14_has_mp3_q15_may_not(self) -> None:
        random.seed(3)
        exam = build_mock_v2_exam(_SURVEY, difficulty=3)
        q14 = exam[13]
        q15 = exam[14]
        self.assertTrue(mock_v2_question_audio_id(q14))
        self.assertIsNotNone(load_question_mp3_bytes(mock_v2_question_audio_id(q14)))
        self.assertEqual(mock_v2_question_audio_id(q15), "")

    def test_all_advanced_pool_mp3_exist(self) -> None:
        for entry in ADVANCED_SET_POOL:
            sid = entry["set_id"]
            for kind in ("comparison", "news_issue"):
                audio_id = f"{sid}_{kind}"
                path = QUESTION_AUDIO_DIR / f"{audio_id}.mp3"
                self.assertTrue(path.is_file(), f"missing {path.name}")


if __name__ == "__main__":
    unittest.main()
