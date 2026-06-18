"""Bound in-session recording blob memory during multi-question exams.

Keeps transcript/metadata on answer rows; drops stale audio bytes from
session-side blob stores so 15-question mocks do not retain 15 recordings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, MutableMapping, Optional, Set

logger = logging.getLogger(__name__)

MAX_RETAINED_RECORDING_BLOBS = 2


def _entry_byte_size(entry: Any) -> int:
    if isinstance(entry, (bytes, bytearray)):
        return len(entry)
    if isinstance(entry, dict):
        raw = entry.get("audio_bytes")
        if raw is not None:
            try:
                return len(bytes(raw))
            except (TypeError, ValueError):
                pass
    return 0


def blob_store_byte_size(store: Dict[Any, Any]) -> int:
    if not isinstance(store, dict):
        return 0
    return sum(_entry_byte_size(v) for v in store.values())


def _recent_question_indices(
    answers: List[Dict[str, Any]],
    index_key: str,
    *,
    max_keep: int = MAX_RETAINED_RECORDING_BLOBS,
) -> Set[int]:
    indices: List[int] = []
    for row in answers:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get(index_key, -1))
        except (TypeError, ValueError):
            continue
        if idx >= 0:
            indices.append(idx)
    unique = sorted(set(indices))
    if len(unique) <= max_keep:
        return set(unique)
    return set(unique[-max_keep:])


def _trim_dict_store(
    store: MutableMapping[Any, Any],
    allowed_keys: Set[Any],
    *,
    flow: str,
) -> int:
    if not isinstance(store, dict) or not store:
        return 0
    before_bytes = blob_store_byte_size(store)
    removed = 0
    for key in list(store.keys()):
        if key not in allowed_keys:
            store.pop(key, None)
            removed += 1
    after_bytes = blob_store_byte_size(store)
    freed = max(0, before_bytes - after_bytes)
    if removed:
        try:
            logger.info(
                "[AUDIO_BLOB_TRIM] flow=%s removed=%s kept=%s bytes_freed=%s",
                flow,
                removed,
                len(store),
                freed,
            )
        except Exception:
            pass
    return removed


def trim_mock_v2_audio_blobs(ss: MutableMapping[str, Any]) -> int:
    answers = ss.get("mock_v2_answers")
    if not isinstance(answers, list):
        return 0
    store = ss.get("mock_v2_audio_blobs")
    if not isinstance(store, dict) or not store:
        return 0
    keep_indices = _recent_question_indices(answers, "question_index")
    allowed_aids: Set[str] = set()
    for row in answers:
        if not isinstance(row, dict):
            continue
        try:
            qi = int(row.get("question_index", -1))
        except (TypeError, ValueError):
            continue
        if qi not in keep_indices:
            continue
        aid = str(row.get("answer_id") or "").strip()
        if aid:
            allowed_aids.add(aid)
    return _trim_dict_store(store, allowed_aids, flow="mock_v2")


def _mock_v2_question_id_for_index(
    questions: List[Dict[str, Any]],
    answers: List[Dict[str, Any]],
    idx: int,
) -> str:
    if isinstance(questions, list) and 0 <= idx < len(questions):
        q = questions[idx]
        if isinstance(q, dict):
            qid = str(q.get("id") or "").strip()
            if qid:
                return qid
    for row in answers:
        if not isinstance(row, dict):
            continue
        try:
            qi = int(row.get("question_index", -1))
        except (TypeError, ValueError):
            continue
        if qi == idx:
            qid = str(row.get("question_id") or "").strip()
            if qid:
                return qid
    return f"mock_v2_q{idx + 1}"


def trim_mock_v2_widget_state(
    ss: MutableMapping[str, Any],
    *,
    questions: Optional[List[Dict[str, Any]]] = None,
    current_index: Optional[int] = None,
) -> int:
    """Drop stale mic/audio/timer session keys; keep recent answered + current index."""
    answers = ss.get("mock_v2_answers")
    if not isinstance(answers, list):
        answers = []
    q_list = questions if isinstance(questions, list) else ss.get("mock_v2_questions")
    if not isinstance(q_list, list):
        q_list = []

    keep_indices = _recent_question_indices(answers, "question_index")
    if current_index is not None:
        try:
            keep_indices.add(int(current_index))
        except (TypeError, ValueError):
            pass

    keep_question_ids: Set[str] = set()
    keep_timer_keys: Set[str] = set()
    for idx in keep_indices:
        if idx < 0:
            continue
        qid = _mock_v2_question_id_for_index(q_list, answers, idx)
        keep_question_ids.add(qid)
        try:
            from components.answer_countdown_timer import build_answer_timer_id

            timer_id = build_answer_timer_id("mock_v2", qid, str(idx))
            keep_timer_keys.add(f"_answer_timer_up_done_{timer_id}")
        except Exception:
            pass

    # Pending mic stash (just_once rerun) — never trim until commit clears _output.
    for key in list(ss.keys()):
        if not isinstance(key, str):
            continue
        if not key.startswith("mock_v2_mic_") or not key.endswith("_output"):
            continue
        if ss.get(key) is None:
            continue
        qid_suffix = key[len("mock_v2_mic_") :][: -len("_output")]
        if qid_suffix:
            keep_question_ids.add(qid_suffix)

    removed = 0
    for key in list(ss.keys()):
        if not isinstance(key, str):
            continue
        drop = False
        if key.startswith("mock_v2_mic_"):
            rest = key[len("mock_v2_mic_") :]
            if rest.endswith("_output"):
                qid_suffix = rest[: -len("_output")]
            else:
                qid_suffix = rest
            drop = qid_suffix not in keep_question_ids
        elif key.startswith("mock_v2_audio_"):
            qid_suffix = key[len("mock_v2_audio_") :]
            drop = qid_suffix not in keep_question_ids
        elif key.startswith("_answer_timer_up_done_mock_v2__"):
            drop = key not in keep_timer_keys
        if drop:
            ss.pop(key, None)
            removed += 1

    if removed:
        try:
            logger.info(
                "[MOCK_V2_WIDGET_TRIM] removed=%s kept_question_ids=%s mic_keys_remaining=%s",
                removed,
                sorted(keep_question_ids),
                sum(
                    1
                    for k in ss.keys()
                    if isinstance(k, str)
                    and (k.startswith("mock_v2_mic_") or k.startswith("mock_v2_audio_"))
                ),
            )
        except Exception:
            pass
    return removed


def trim_mini_v2_audio_blobs(ss: MutableMapping[str, Any]) -> int:
    answers = ss.get("mini_v2_answers")
    if not isinstance(answers, list):
        return 0
    store = ss.get("mini_v2_audio_blobs")
    if not isinstance(store, dict) or not store:
        return 0
    keep_indices = _recent_question_indices(answers, "question_index")
    allowed_keys: Set[Any] = set(keep_indices)
    return _trim_dict_store(store, allowed_keys, flow="mini_v2")


def trim_topic_v2_audio_blobs(
    ss: MutableMapping[str, Any],
    *,
    topic: Optional[str] = None,
) -> int:
    answers = ss.get("topic_v2_answers")
    if not isinstance(answers, list):
        return 0
    store = ss.get("topic_v2_audio_blobs")
    if not isinstance(store, dict) or not store:
        return 0

    active_topic = str(topic or ss.get("topic_v2_topic") or "").strip()
    filtered: List[Dict[str, Any]] = []
    for row in answers:
        if not isinstance(row, dict):
            continue
        row_topic = str(row.get("topic_id") or row.get("topic") or active_topic or "").strip()
        if active_topic and row_topic and row_topic != active_topic:
            continue
        filtered.append(row)

    keep_indices = _recent_question_indices(filtered, "q_index")
    allowed_keys: Set[str] = set()
    for row in filtered:
        try:
            qi = int(row.get("q_index", -1))
        except (TypeError, ValueError):
            continue
        if qi not in keep_indices:
            continue
        row_topic = str(row.get("topic_id") or row.get("topic") or active_topic or "").strip()
        if row_topic:
            allowed_keys.add(f"{row_topic}\t{qi}")
        aid = str(row.get("answer_id") or "").strip()
        if aid:
            allowed_keys.add(f"aid:{aid}")

    removed = 0
    before_bytes = blob_store_byte_size(store)
    for key in list(store.keys()):
        if str(key) not in allowed_keys:
            store.pop(key, None)
            removed += 1
    if removed:
        freed = max(0, before_bytes - blob_store_byte_size(store))
        try:
            logger.info(
                "[AUDIO_BLOB_TRIM] flow=topic_v2 removed=%s kept=%s bytes_freed=%s",
                removed,
                len(store),
                freed,
            )
        except Exception:
            pass
    return removed


def trim_legacy_mock_recordings(mx: Dict[str, Any]) -> int:
    """Keep ``mx['recordings']`` to the two most recently answered questions."""
    rec = mx.get("recordings")
    if not isinstance(rec, dict) or not rec:
        return 0
    results = mx.get("results")
    if not isinstance(results, list):
        return 0

    keyed: List[tuple[int, str]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        audio_key = str(row.get("audio_key") or "").strip()
        if not audio_key or audio_key not in rec:
            continue
        try:
            qi = int(row.get("question_index", -1))
        except (TypeError, ValueError):
            qi = -1
        if qi >= 0:
            keyed.append((qi, audio_key))

    if not keyed:
        return 0

    keyed.sort(key=lambda pair: pair[0])
    allowed_keys = {ak for _, ak in keyed[-MAX_RETAINED_RECORDING_BLOBS:]}
    removed = _trim_dict_store(rec, allowed_keys, flow="legacy_real_mock")

    current_blob = mx.get("audio_bytes")
    if current_blob is not None and allowed_keys:
        keep_blob = False
        for ak in allowed_keys:
            if rec.get(ak) is current_blob:
                keep_blob = True
                break
        if not keep_blob and not any(rec.get(ak) == current_blob for ak in rec):
            mx.pop("audio_bytes", None)
    return removed


def trim_v2_flow_audio_blobs(ss: MutableMapping[str, Any]) -> None:
    """Trim all V2 blob stores before disk persist."""
    trim_mock_v2_audio_blobs(ss)
    trim_mini_v2_audio_blobs(ss)
    trim_topic_v2_audio_blobs(ss)
