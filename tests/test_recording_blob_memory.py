"""Tests for in-session recording blob memory bounds and V2 snapshot audio exclusion."""

from __future__ import annotations

import unittest
from typing import Any, Dict
from unittest.mock import patch

from utils.recording_blob_memory import (
    MAX_RETAINED_RECORDING_BLOBS,
    blob_store_byte_size,
    trim_legacy_mock_recordings,
    trim_mini_v2_audio_blobs,
    trim_mock_v2_audio_blobs,
    trim_mock_v2_widget_state,
    trim_topic_v2_audio_blobs,
)
from utils.v2_flow_persistence import (
    _build_mini_v2_snapshot,
    _build_mock_v2_snapshot,
    _build_topic_v2_snapshot,
    _apply_snapshot,
    _snapshot_meaningful_topic_v2,
    clear_topic_v2_disk_snapshot,
    get_v2_resume_offer,
    maybe_restore_v2_flows_from_disk,
    persist_v2_flows_now,
    resume_v2_flow,
)


def _blob(size: int) -> Dict[str, Any]:
    return {"audio_bytes": b"x" * size, "mime_type": "audio/webm"}


class RecordingBlobMemoryTests(unittest.TestCase):
    def test_mock_v2_fifteen_questions_keeps_two_blobs(self) -> None:
        ss: Dict[str, Any] = {"mock_v2_answers": [], "mock_v2_audio_blobs": {}}
        blob_size = 50_000
        for i in range(15):
            aid = f"aid-{i}"
            ss["mock_v2_answers"].append(
                {
                    "question_index": i,
                    "answer_id": aid,
                    "transcript": f"answer text {i}",
                    "student_answer": f"answer text {i}",
                }
            )
            ss["mock_v2_audio_blobs"][aid] = _blob(blob_size)
            trim_mock_v2_audio_blobs(ss)

        self.assertLessEqual(len(ss["mock_v2_audio_blobs"]), MAX_RETAINED_RECORDING_BLOBS)
        self.assertIn("aid-13", ss["mock_v2_audio_blobs"])
        self.assertIn("aid-14", ss["mock_v2_audio_blobs"])
        self.assertNotIn("aid-0", ss["mock_v2_audio_blobs"])
        self.assertLessEqual(blob_store_byte_size(ss["mock_v2_audio_blobs"]), blob_size * 2)

    def test_mock_v2_transcripts_preserved_after_trim(self) -> None:
        ss: Dict[str, Any] = {"mock_v2_answers": [], "mock_v2_audio_blobs": {}}
        for i in range(5):
            ss["mock_v2_answers"].append(
                {
                    "question_index": i,
                    "answer_id": f"aid-{i}",
                    "transcript": f"t{i}",
                }
            )
            ss["mock_v2_audio_blobs"][f"aid-{i}"] = _blob(1000)
            trim_mock_v2_audio_blobs(ss)
        self.assertEqual(len(ss["mock_v2_answers"]), 5)
        self.assertEqual(ss["mock_v2_answers"][0]["transcript"], "t0")

    def test_mock_v2_widget_state_fifteen_questions_keeps_two_mic_keys(self) -> None:
        from components.answer_countdown_timer import build_answer_timer_id

        questions = [
            {"id": f"q{i}", "question_index": i, "question_number": i + 1}
            for i in range(15)
        ]
        ss: Dict[str, Any] = {
            "mock_v2_questions": questions,
            "mock_v2_answers": [],
        }
        for i in range(15):
            qid = f"q{i}"
            ss["mock_v2_answers"].append(
                {
                    "question_index": i,
                    "question_id": qid,
                    "answer_id": f"aid-{i}",
                    "transcript": f"t{i}",
                }
            )
            ss[f"mock_v2_mic_{qid}"] = {"bytes": b"mic"}
            ss[f"mock_v2_mic_{qid}_output"] = {"bytes": b"mic"}
            ss[f"mock_v2_audio_{qid}"] = {"bytes": b"alt"}
            tid = build_answer_timer_id("mock_v2", qid, str(i))
            ss[f"_answer_timer_up_done_{tid}"] = True
            trim_mock_v2_widget_state(ss, questions=questions, current_index=i)
            ss.pop(f"mock_v2_mic_{qid}_output", None)

        mic_keys = [
            k
            for k in ss
            if isinstance(k, str)
            and (k.startswith("mock_v2_mic_") or k.startswith("mock_v2_audio_"))
        ]
        self.assertLessEqual(len(mic_keys), MAX_RETAINED_RECORDING_BLOBS * 3)
        self.assertIn("mock_v2_mic_q13", ss)
        self.assertIn("mock_v2_mic_q14", ss)
        self.assertNotIn("mock_v2_mic_q0", ss)
        self.assertNotIn("mock_v2_audio_q0", ss)

    def test_mock_v2_widget_trim_keeps_pending_stash_output(self) -> None:
        questions = [{"id": "q14", "question_index": 14, "question_number": 15}]
        ss: Dict[str, Any] = {
            "mock_v2_questions": questions,
            "mock_v2_answers": [
                {
                    "question_index": i,
                    "question_id": f"q{i}",
                    "answer_id": f"aid-{i}",
                    "transcript": f"t{i}",
                }
                for i in range(14)
            ],
            "mock_v2_mic_q0": {"bytes": b"old"},
            "mock_v2_mic_q14_output": {"bytes": b"pending"},
        }
        trim_mock_v2_widget_state(ss, questions=questions, current_index=14)
        self.assertIn("mock_v2_mic_q14_output", ss)
        self.assertNotIn("mock_v2_mic_q0", ss)

    def test_mini_v2_fifteen_questions_keeps_two_blobs(self) -> None:
        ss: Dict[str, Any] = {"mini_v2_answers": [], "mini_v2_audio_blobs": {}}
        for i in range(15):
            ss["mini_v2_answers"].append(
                {"question_index": i, "transcript": f"t{i}"}
            )
            ss["mini_v2_audio_blobs"][i] = _blob(40_000)
            trim_mini_v2_audio_blobs(ss)
        self.assertLessEqual(len(ss["mini_v2_audio_blobs"]), MAX_RETAINED_RECORDING_BLOBS)
        self.assertIn(13, ss["mini_v2_audio_blobs"])
        self.assertIn(14, ss["mini_v2_audio_blobs"])

    def test_topic_v2_keeps_two_question_blobs(self) -> None:
        topic = "movies_tv"
        ss: Dict[str, Any] = {
            "topic_v2_topic": topic,
            "topic_v2_answers": [],
            "topic_v2_audio_blobs": {},
        }
        for i in range(3):
            aid = f"a{i}"
            ss["topic_v2_answers"].append(
                {"topic_id": topic, "q_index": i, "answer_id": aid, "transcript": f"t{i}"}
            )
            ss["topic_v2_audio_blobs"][f"{topic}\t{i}"] = _blob(30_000)
            ss["topic_v2_audio_blobs"][f"aid:{aid}"] = _blob(30_000)
            trim_topic_v2_audio_blobs(ss)
        self.assertLessEqual(len(ss["topic_v2_audio_blobs"]), 4)
        self.assertIn(f"{topic}\t1", ss["topic_v2_audio_blobs"])
        self.assertIn(f"{topic}\t2", ss["topic_v2_audio_blobs"])
        self.assertNotIn(f"{topic}\t0", ss["topic_v2_audio_blobs"])

    def test_legacy_real_mock_recordings_trim(self) -> None:
        mx: Dict[str, Any] = {"results": [], "recordings": {}}
        for i in range(5):
            ak = f"q_{100 + i}"
            mx["recordings"][ak] = b"audio" * 1000
            mx["results"].append(
                {"question_index": i, "audio_key": ak, "result": {"transcript": f"t{i}"}}
            )
            trim_legacy_mock_recordings(mx)
        self.assertLessEqual(len(mx["recordings"]), MAX_RETAINED_RECORDING_BLOBS)
        self.assertIn("q_103", mx["recordings"])
        self.assertIn("q_104", mx["recordings"])


class V2SnapshotAudioExclusionTests(unittest.TestCase):
    def test_mock_v2_snapshot_excludes_audio_blobs(self) -> None:
        ss = {
            "mock_mode": "mock_v2",
            "mock_v2_step": "saved",
            "mock_v2_answers": [{"question_index": 0, "transcript": "hi"}],
            "mock_v2_audio_blobs": {"aid-0": _blob(5000)},
            "mock_v2_index": 0,
        }
        snap = _build_mock_v2_snapshot(ss)
        self.assertNotIn("mock_v2_audio_blobs", snap)
        self.assertIn("mock_v2_answers", snap)

    def test_mini_v2_snapshot_excludes_audio_blobs(self) -> None:
        ss = {
            "mini_mock_v2_active": True,
            "mini_v2_step": "saved",
            "mini_v2_answers": [{"question_index": 0, "transcript": "hi"}],
            "mini_v2_audio_blobs": {0: _blob(5000)},
            "mini_v2_index": 0,
            "mini_v2_questions": [
                {"question_index": 0, "question_en": "Q1", "type_label": "묘사"},
            ],
        }
        snap = _build_mini_v2_snapshot(ss)
        self.assertNotIn("mini_v2_audio_blobs", snap)
        self.assertIn("mini_v2_answers", snap)
        self.assertIn("mini_v2_questions", snap)

    def test_restore_skips_legacy_audio_blobs_in_snapshot(self) -> None:
        ss: Dict[str, Any] = {}
        old_snap = {
            "mock_v2_answers": [{"question_index": 0, "transcript": "restored"}],
            "mock_v2_index": 1,
            "mock_v2_step": "question",
            "mock_v2_audio_blobs": {"aid-0": {"__b64__": "eHh4"}},
        }
        _apply_snapshot(ss, old_snap)
        self.assertEqual(len(ss.get("mock_v2_answers") or []), 1)
        self.assertNotIn("mock_v2_audio_blobs", ss)

    @patch("utils.user_progress_store.save_user_progress")
    @patch("utils.user_progress_store.load_user_progress", return_value={})
    def test_persist_trims_before_write(self, _load, _save) -> None:
        from utils.v2_flow_persistence import persist_v2_flows_now

        ss: Dict[str, Any] = {
            "entry_gate_completed": True,
            "mock_mode": "mock_v2",
            "mock_v2_step": "saved",
            "mock_v2_answers": [],
            "mock_v2_audio_blobs": {},
        }
        for i in range(5):
            aid = f"aid-{i}"
            ss["mock_v2_answers"].append({"question_index": i, "answer_id": aid})
            ss["mock_v2_audio_blobs"][aid] = _blob(10_000)
        persist_v2_flows_now(ss)
        self.assertLessEqual(len(ss["mock_v2_audio_blobs"]), MAX_RETAINED_RECORDING_BLOBS)
        saved = _save.call_args[0][0]
        snap = saved.get("mock_v2_snapshot") or {}
        self.assertNotIn("mock_v2_audio_blobs", snap)


class TopicV2SnapshotTests(unittest.TestCase):
    def test_topic_v2_snapshot_excludes_audio_blobs(self) -> None:
        ss = {
            "topic_v2_step": "saved",
            "topic_v2_question_index": 0,
            "topic_v2_mode": "topic",
            "topic_v2_topic": "movies_tv",
            "topic_v2_practice_sig": "abc123",
            "topic_v2_questions": [{"en": "Q1", "ko": "질문1"}],
            "topic_v2_current_question": {"en": "Q1", "ko": "질문1"},
            "topic_v2_answers": [{"q_index": 0, "transcript": "hello", "topic": "movies_tv"}],
            "topic_v2_audio_blobs": {"movies_tv\t0": _blob(5000)},
            "topicv2_mic_abc123_0_output": {"bytes": b"mic"},
        }
        snap = _build_topic_v2_snapshot(ss)
        self.assertIn("topic_v2_answers", snap)
        self.assertIn("topic_v2_step", snap)
        self.assertIn("topic_v2_questions", snap)
        self.assertNotIn("topic_v2_audio_blobs", snap)
        self.assertNotIn("topicv2_mic_abc123_0_output", snap)
        self.assertEqual(snap["_resume_hint"]["mock_page"], "TOPIC_V2")

    def test_snapshot_meaningful_topic_v2_requires_answers(self) -> None:
        self.assertFalse(_snapshot_meaningful_topic_v2({}))
        self.assertFalse(
            _snapshot_meaningful_topic_v2(
                {"topic_v2_step": "select_topic", "topic_v2_answers": []}
            )
        )
        self.assertTrue(
            _snapshot_meaningful_topic_v2(
                {"topic_v2_step": "saved", "topic_v2_answers": [{"q_index": 0}]}
            )
        )

    @patch("utils.user_progress_store.save_user_progress")
    @patch("utils.user_progress_store.load_user_progress", return_value={})
    def test_persist_writes_topic_v2_snapshot(self, _load, _save) -> None:
        ss: Dict[str, Any] = {
            "entry_gate_completed": True,
            "topic_v2_step": "saved",
            "topic_v2_question_index": 0,
            "topic_v2_mode": "topic",
            "topic_v2_topic": "cafe",
            "topic_v2_practice_sig": "sig1",
            "topic_v2_questions": [{"en": "Q1", "ko": "질문"}],
            "topic_v2_current_question": {"en": "Q1", "ko": "질문"},
            "topic_v2_answers": [{"q_index": 0, "transcript": "hi", "topic": "cafe"}],
            "topic_v2_audio_blobs": {"cafe\t0": _blob(8000)},
        }
        persist_v2_flows_now(ss)
        saved = _save.call_args[0][0]
        snap = saved.get("topic_v2_snapshot") or {}
        self.assertIn("topic_v2_answers", snap)
        self.assertNotIn("topic_v2_audio_blobs", snap)

    @patch("utils.user_progress_store.save_user_progress")
    @patch("utils.user_progress_store.load_user_progress", return_value={"topic_v2_snapshot": {"topic_v2_answers": []}})
    def test_clear_topic_v2_disk_snapshot(self, _load, _save) -> None:
        ss: Dict[str, Any] = {}
        clear_topic_v2_disk_snapshot(ss)
        saved = _save.call_args[0][0]
        self.assertNotIn("topic_v2_snapshot", saved)


class TopicV2RestoreResumeTests(unittest.TestCase):
    def _topic_snap(self) -> Dict[str, Any]:
        return {
            "topic_v2_step": "saved",
            "topic_v2_question_index": 1,
            "topic_v2_mode": "topic",
            "topic_v2_topic": "cafe",
            "topic_v2_practice_sig": "sig1",
            "topic_v2_questions": [{"en": "Q1"}, {"en": "Q2"}, {"en": "Q3"}],
            "topic_v2_current_question": {"en": "Q2"},
            "topic_v2_answers": [{"q_index": 0, "transcript": "hello", "topic": "cafe"}],
            "topic_v2_feedback": None,
            "topic_v2_feedback_by_q": {},
            "_resume_hint": {"mock_page": "TOPIC_V2"},
        }

    @patch("utils.user_progress_store.load_user_progress")
    def test_maybe_restore_topic_v2_data_only(self, load_prog) -> None:
        load_prog.return_value = {"topic_v2_snapshot": self._topic_snap()}
        ss: Dict[str, Any] = {"entry_gate_completed": True}
        self.assertTrue(maybe_restore_v2_flows_from_disk(ss))
        self.assertEqual(ss.get("topic_v2_step"), "saved")
        self.assertEqual(ss.get("topic_v2_question_index"), 1)
        self.assertEqual(len(ss.get("topic_v2_answers") or []), 1)
        self.assertNotIn("mock_page", ss)

    def test_get_v2_resume_offer_topic_v2(self) -> None:
        ss: Dict[str, Any] = {}
        prog = {"topic_v2_snapshot": self._topic_snap()}
        offer = get_v2_resume_offer(ss, prog)
        self.assertIsNotNone(offer)
        assert offer is not None
        self.assertEqual(offer.get("flow"), "topic_v2")
        self.assertEqual(offer.get("label"), "주제별 연습 이어서 풀기")
        self.assertIn("카페", str(offer.get("practice_label") or ""))

    def test_get_v2_resume_offer_skips_empty_topic_answers(self) -> None:
        snap = dict(self._topic_snap())
        snap["topic_v2_answers"] = []
        offer = get_v2_resume_offer({}, {"topic_v2_snapshot": snap})
        self.assertIsNone(offer)

    def test_resume_v2_flow_topic_routing(self) -> None:
        ss: Dict[str, Any] = {"mock": {}}
        resume_v2_flow(ss, flow="topic_v2")
        self.assertEqual(ss.get("mock_mode"), "topic_practice_v2")
        self.assertEqual(ss.get("mock_page"), "TOPIC_V2")
        self.assertTrue(ss.get("practice_portal_selected"))
        self.assertTrue(ss.get("_v2_user_resumed"))


if __name__ == "__main__":
    unittest.main()
