"""
Topic practice full report — transcript-first or one-call audio batch.

At most ONE Gemini call per report request. Never sequential Q1/Q2/Q3 analysis.
Local fallback is never shown as a completed report.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from services.evaluation import ai_diag
from services.evaluation.audio_mime import resolve_audio_mime
from utils.ai_pending_diag import (
    analysis_error_short,
    classify_ai_error,
    log_ai_pending_reason,
)
from utils.speech_recording import recording_byte_length
from utils.text_utils import is_real_speech_transcript

logger = logging.getLogger(__name__)

TOPIC_MINI_REPORT_ONE_CALL_ONLY = True
ALLOW_TOPIC_SEQUENTIAL_ANALYSIS = False
AUTO_LOCAL_FALLBACK_AS_REPORT = False
MIN_MEANINGFUL_TRANSCRIPTS_FOR_TEXT_ONLY = 2
MIN_TRANSCRIPT_LEN = 10

TOPIC_REPORT_NOT_STARTED = "not_started"
TOPIC_REPORT_ANALYZING = "analyzing"
TOPIC_REPORT_COMPLETED = "completed"
TOPIC_REPORT_PENDING_RETRY = "pending_retry"
TOPIC_REPORT_FAILED = "failed"

MAX_TOPIC_MINI_TOTAL_AUDIO_BYTES = 8 * 1024 * 1024
MAX_TOPIC_MINI_PER_AUDIO_BYTES = 4 * 1024 * 1024

_REAL_REPORT_SOURCES = frozenset(
    {"gemini_text_only", "gemini_one_call_audio_batch", "gemini_one_call"}
)

_TRANSCRIPT_FIELD_ORDER = (
    "transcript",
    "restored_transcript",
    "heard_raw",
    "answer_text",
    "recognized_text",
    "transcription",
)

_PLACEHOLDER_TRANSCRIPT = frozenset(
    {
        "no speech",
        "no_speech",
        "unclear",
        "none",
        "n/a",
        "na",
        "null",
        "empty",
        "silence",
    }
)

_DEFAULT_RETRY_MISSIONS = [
    "Q1: 첫 문장을 Let me tell you about... 으로 시작해 보기",
    "Q2: The main reason is that... 사용해 보기",
    "Q3: Overall, I'd say... 로 마무리하기",
]


def _diag_log(msg: str) -> None:
    logger.info("[TOPIC_REPORT_DIAG] %s", msg)


def is_real_topic_ai_report(report: Any) -> bool:
    """True only for a real Gemini topic report (not local fallback)."""
    if not isinstance(report, dict):
        return False
    if report.get("local_fallback"):
        return False
    return str(report.get("report_source") or "") in _REAL_REPORT_SOURCES


def get_meaningful_transcript(answer: Dict[str, Any]) -> Optional[str]:
    """Return a usable transcript string from a saved answer row, or None."""
    if not isinstance(answer, dict):
        return None
    res = answer.get("analysis_result")
    sources: List[Dict[str, Any]] = [answer]
    if isinstance(res, dict):
        sources.append(res)
    for src in sources:
        for key in _TRANSCRIPT_FIELD_ORDER:
            raw = src.get(key)
            if raw is None:
                continue
            text = str(raw).strip()
            if len(text) < MIN_TRANSCRIPT_LEN:
                continue
            low = text.lower()
            if low in _PLACEHOLDER_TRANSCRIPT:
                continue
            if not is_real_speech_transcript(text):
                continue
            return text
    return None


def _result_completed(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "topic_report_status": TOPIC_REPORT_COMPLETED,
        "report": report,
    }


def _result_pending_retry(*, reason: str, saved_count: int = 3) -> Dict[str, Any]:
    _diag_log(f"report_status=pending_retry | reason={reason[:120]}")
    return {
        "topic_report_status": TOPIC_REPORT_PENDING_RETRY,
        "report": None,
        "pending_reason": reason,
        "saved_count": saved_count,
    }


def _result_failed(user_message: str) -> Dict[str, Any]:
    return {
        "topic_report_status": TOPIC_REPORT_FAILED,
        "report": None,
        "user_message": user_message,
    }


def _normalize_grammar_row(row: Any) -> Dict[str, str]:
    if not isinstance(row, dict):
        return {}
    wrong = str(
        row.get("wrong")
        or row.get("before")
        or row.get("original")
        or ""
    ).strip()
    right = str(
        row.get("right")
        or row.get("after")
        or row.get("corrected")
        or ""
    ).strip()
    note = str(row.get("note") or row.get("why") or row.get("reason") or "").strip()
    if not wrong and not right:
        return {}
    return {"wrong": wrong, "right": right, "note": note}


def _normalize_expression_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    phrase = str(row.get("phrase") or row.get("original") or row.get("before") or "").strip()
    alts = row.get("alternatives") or row.get("upgrades") or row.get("better") or []
    if isinstance(alts, str):
        alts = [alts]
    alts = [str(a).strip() for a in alts if str(a).strip()]
    upgrade = str(row.get("upgrade") or "").strip()
    if upgrade and upgrade not in alts:
        alts.insert(0, upgrade)
    note = str(row.get("note") or row.get("why") or row.get("reason") or "").strip()
    if not phrase and not alts:
        return {}
    return {"phrase": phrase, "alternatives": alts[:3], "note": note}


def _question_label(q_idx: int) -> str:
    return f"Q{int(q_idx) + 1}"


def _map_topic_report_payload(
    topic_report: Dict[str, Any],
    *,
    topic_title: str,
    report_source: str,
    restored: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    tr = topic_report if isinstance(topic_report, dict) else {}
    grammar = [
        g
        for g in (_normalize_grammar_row(r) for r in (tr.get("grammar_corrections") or []))
        if g
    ][:4]
    expressions = [
        e
        for e in (_normalize_expression_row(r) for r in (tr.get("expression_upgrades") or []))
        if e
    ][:4]
    strengths = [str(s).strip() for s in (tr.get("strengths") or []) if str(s).strip()][:2]
    missions = [str(m).strip() for m in (tr.get("missions") or []) if str(m).strip()][:2]
    if not missions:
        missions = [
            str(m).strip()
            for m in (tr.get("structure_missions") or [])
            if str(m).strip()
        ][:2]

    structure_fb = tr.get("structure_feedback")
    if not isinstance(structure_fb, dict):
        structure_fb = {
            "good": tr.get("structure_good") or [],
            "missing": tr.get("structure_missing") or [],
            "next": str(tr.get("structure_next") or ""),
        }

    improved: List[Dict[str, str]] = []
    for item in tr.get("improved_sentences") or []:
        if not isinstance(item, dict):
            continue
        lbl = str(item.get("question_label") or item.get("label") or "").strip()
        sent = str(item.get("sentence") or item.get("text") or "").strip()
        if sent:
            improved.append({"question_label": lbl or "Q?", "sentence": sent})
    retry_flat = [x["sentence"] for x in improved if x.get("sentence")]
    if len(retry_flat) < 3:
        for s in tr.get("retry_sentences") or []:
            if isinstance(s, str) and s.strip():
                retry_flat.append(s.strip())
    retry_flat = retry_flat[:3]
    if len(retry_flat) < 3:
        retry_flat.extend(_DEFAULT_RETRY_MISSIONS[len(retry_flat) : 3])

    flow = str(
        tr.get("overall_flow_summary") or tr.get("flow_summary") or ""
    ).strip()

    restored_list = restored if isinstance(restored, list) else []
    if not restored_list:
        for item in tr.get("question_summaries") or []:
            if not isinstance(item, dict):
                continue
            lbl = str(item.get("question_label") or "").strip()
            tr_text = str(item.get("transcript") or "").strip()
            if lbl and tr_text:
                restored_list.append(
                    {
                        "question_label": lbl,
                        "transcript": tr_text,
                        "language_status": str(item.get("status") or "english"),
                    }
                )

    return {
        "topic_title": topic_title,
        "flow_summary": flow or f"「{topic_title}」 주제로 세 답변을 함께 살펴봤어요.",
        "overall_flow_summary": flow,
        "strengths": strengths
        or ["세 답변 모두 주제에 맞게 이어 말했어요.", "핵심 내용을 중심으로 답을 시작했어요."],
        "grammar_corrections": grammar,
        "expression_upgrades": expressions,
        "structure_feedback": structure_fb,
        "structure_missions": missions
        or [
            "각 답변 마지막에 Overall, I'd say... 로 마무리해 보세요.",
            "이유를 말한 뒤 To be more specific,... 으로 예시를 하나 붙여 보세요.",
        ],
        "missions": missions or [],
        "improved_sentences": improved,
        "retry_sentences": retry_flat,
        "restored_transcripts": restored_list,
        "question_summaries": tr.get("question_summaries") or [],
        "issue_notes": [],
        "analyzed_count": len([r for r in restored_list if r.get("transcript")]),
        "report_source": report_source,
        "local_fallback": False,
        "api_pending": False,
    }


def _build_text_only_prompt(
    topic_title: str,
    topic_category: str,
    payloads: List[Dict[str, Any]],
    *,
    meaningful: List[Tuple[int, str]],
) -> str:
    lines = [
        "You are an expert OPIc speaking coach.",
        f'Topic title: "{topic_title}"',
        f"Topic category: {topic_category or 'general'}",
        "",
        "Analyze these topic practice answers and generate ONE Korean full topic report.",
        "Use ONLY the transcripts provided. Do NOT invent missing answers.",
        "",
        "Return ONLY one JSON object (no markdown fences):",
        "{",
        '  "overall_flow_summary": "<2-3 Korean sentences>",',
        '  "strengths": ["...", "..."],',
        '  "grammar_corrections": [{"before":"...","after":"...","why":"..."}],',
        '  "expression_upgrades": [{"before":"...","better":["..."],"why":"..."}],',
        '  "structure_feedback": {"good":["..."],"missing":["..."],"next":"..."},',
        '  "missions": ["...", "..."],',
        '  "improved_sentences": [',
        '    {"question_label":"Q1","sentence":"..."},',
        '    {"question_label":"Q2","sentence":"..."},',
        '    {"question_label":"Q3","sentence":"..."}',
        "  ],",
        '  "question_summaries": [',
        '    {"question_label":"Q1","summary":"...","status":"analyzed|partial|missing"}',
        "  ]",
        "}",
        "",
        "Answers:",
    ]
    meaningful_by_idx = {idx: text for idx, text in meaningful}
    for p in payloads:
        q_idx = int(p.get("question_index") or 0)
        lbl = _question_label(q_idx)
        qtext = str(p.get("question_text") or "").strip()
        tr = meaningful_by_idx.get(q_idx)
        lines.append(f"{lbl} question: {qtext}")
        if tr:
            lines.append(f"{lbl} transcript: {tr}")
        else:
            lines.append(f"{lbl} transcript: (not available — note in report)")
        lines.append("")
    return "\n".join(lines)


def _build_audio_batch_prompt(
    topic_title: str,
    topic_category: str,
    payloads: List[Dict[str, Any]],
    difficulty: int,
) -> str:
    lines = [
        "You are an expert OPIc speaking coach.",
        f'Topic: "{topic_title}" ({topic_category or "general"}).',
        "",
        "You will receive THREE audio answers from one topic practice set.",
        "For each answer: restore the student's spoken English as accurately as possible.",
        "Then produce ONE Korean full topic report across all 3 answers.",
        "Do NOT assign numeric OPIc levels.",
        "",
        "Return ONLY one JSON object (no markdown fences):",
        "{",
        '  "restored_answers": [',
        "    {",
        '      "question_label": "Q1",',
        '      "question_index": 0,',
        '      "transcript": "<verbatim English>",',
        '      "language_status": "english|non_english|unclear",',
        '      "short_note": "<brief Korean note>"',
        "    }",
        "  ],",
        '  "topic_report": {',
        '    "overall_flow_summary": "...",',
        '    "strengths": ["...", "..."],',
        '    "grammar_corrections": [{"before":"...","after":"...","why":"..."}],',
        '    "expression_upgrades": [{"before":"...","better":["..."],"why":"..."}],',
        '    "structure_feedback": {"good":["..."],"missing":["..."],"next":"..."},',
        '    "missions": ["...", "..."],',
        '    "improved_sentences": [{"question_label":"Q1","sentence":"..."}],',
        '    "question_summaries": [{"question_label":"Q1","summary":"...","status":"..."}]',
        "  }",
        "}",
        "",
        f"Difficulty hint: {int(difficulty)}.",
        "",
        "Question context (do not echo as user speech):",
    ]
    for p in payloads:
        qn = int(p.get("question_index") or 0) + 1
        lines.append(f"Q{qn}: {p.get('question_text', '')}")
    lines.append("")
    lines.append("Audio parts follow in order Q1, Q2, Q3.")
    return "\n".join(lines)


def _gemini_generate(
    *,
    api_key: str,
    parts: List[Any],
    path: str,
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """One Gemini call. Returns (parsed_json, error_message, model_used)."""
    from google import genai
    from google.genai import types as genai_types

    from services.evaluation.gemini_multimodal_pipeline import (
        _build_model_candidates,
        _extract_json_object,
    )
    from services.evaluation.eval_config import MODEL_NAME

    client = genai.Client(api_key=api_key)
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(temperature=0.3, max_output_tokens=8192)

    model_candidates = _build_model_candidates()
    last_error = ""
    for candidate in model_candidates:
        _diag_log(f"gemini_call_start | path={path} | model={candidate}")
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            err_text = str(exc)
            if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                return None, last_error, candidate
            if "404" in err_text or "NOT_FOUND" in err_text:
                continue
            continue

        raw_text = (getattr(response, "text", "") or "").strip()
        if not raw_text:
            for cand in getattr(response, "candidates", None) or []:
                content = getattr(cand, "content", None)
                for part in getattr(content, "parts", None) or []:
                    t = getattr(part, "text", None)
                    if t:
                        raw_text = (raw_text + "\n" + t).strip()
        if not raw_text:
            last_error = "AI 응답이 비어 있었습니다."
            _diag_log(
                f"gemini_call_failed | path={path} | category=empty_response | short_error=empty"
            )
            continue

        _diag_log(f"gemini_call_success | path={path} | response_chars={len(raw_text)}")
        parsed = _extract_json_object(raw_text)
        if not isinstance(parsed, dict):
            last_error = "미니 리포트 JSON 파싱 실패"
            _diag_log(
                f"gemini_call_failed | path={path} | category=response_parse_error"
            )
            continue
        return parsed, "", candidate

    return None, last_error or f"모델 호출 실패 ({MODEL_NAME})", ""


def _path_text_only(
    payloads: List[Dict[str, Any]],
    *,
    topic_title: str,
    topic_category: str,
    meaningful: List[Tuple[int, str]],
    api_key: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    from google.genai import types as genai_types

    _diag_log("path=text_only")
    _diag_log("using_text_only_report=True")
    _diag_log("audio_resend=False")
    _diag_log("planned_gemini_calls=1")

    prompt = _build_text_only_prompt(
        topic_title, topic_category, payloads, meaningful=meaningful
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    parsed, err, model = _gemini_generate(api_key=api_key, parts=parts, path="text_only")
    if not parsed or err:
        return None, err

    report = _map_topic_report_payload(
        parsed,
        topic_title=topic_title,
        report_source="gemini_text_only",
        restored=[
            {
                "question_label": _question_label(idx),
                "transcript": text,
                "language_status": "english",
            }
            for idx, text in meaningful
        ],
    )
    report["model_used"] = model
    return report, ""


def _path_one_call_audio_batch(
    payloads: List[Dict[str, Any]],
    *,
    topic_title: str,
    topic_category: str,
    api_key: str,
    difficulty: int,
) -> Tuple[Optional[Dict[str, Any]], str, Optional[Dict[str, Any]]]:
    from google.genai import types as genai_types

    audio_parts = sum(1 for p in payloads if p.get("audio_bytes"))
    total_bytes = sum(len(p["audio_bytes"]) for p in payloads if p.get("audio_bytes"))
    _diag_log("path=one_call_audio_batch")
    _diag_log(f"saved_answers={len(payloads)}")
    _diag_log("planned_gemini_calls=1")
    _diag_log(f"audio_parts={audio_parts}")
    _diag_log(f"total_audio_bytes={total_bytes}")

    prompt = _build_audio_batch_prompt(
        topic_title, topic_category, payloads, difficulty
    )
    parts: List[Any] = [genai_types.Part.from_text(text=prompt)]
    for p in payloads:
        qn = int(p.get("question_index") or 0) + 1
        qtext = str(p.get("question_text") or "").strip()
        parts.append(genai_types.Part.from_text(text=f"--- Answer Q{qn} ---\n{qtext}"))
        blob = p.get("audio_bytes")
        if not isinstance(blob, (bytes, bytearray)) or not blob:
            continue
        mime = str(p.get("mime_type") or "").strip() or resolve_audio_mime(bytes(blob))
        parts.append(genai_types.Part.from_bytes(data=bytes(blob), mime_type=mime))

    parsed, err, model = _gemini_generate(
        api_key=api_key, parts=parts, path="one_call_audio_batch"
    )
    if not parsed or err:
        return None, err, None

    restored_raw = parsed.get("restored_answers") or []
    restored_list: List[Dict[str, Any]] = []
    if isinstance(restored_raw, list):
        for item in restored_raw:
            if not isinstance(item, dict):
                continue
            lbl = str(item.get("question_label") or "").strip()
            tr = str(item.get("transcript") or "").strip()
            q_idx = item.get("question_index")
            if q_idx is None and lbl:
                m = re.match(r"Q(\d+)", lbl, re.I)
                if m:
                    q_idx = int(m.group(1)) - 1
            restored_list.append(
                {
                    "question_label": lbl or _question_label(int(q_idx or 0)),
                    "question_index": int(q_idx) if q_idx is not None else -1,
                    "transcript": tr,
                    "language_status": str(item.get("language_status") or "english"),
                    "short_note": str(item.get("short_note") or ""),
                }
            )

    topic_report = parsed.get("topic_report")
    if not isinstance(topic_report, dict):
        topic_report = parsed

    report = _map_topic_report_payload(
        topic_report,
        topic_title=topic_title,
        report_source="gemini_one_call_audio_batch",
        restored=restored_list,
    )
    report["model_used"] = model
    return report, "", parsed


def _prepare_saved_answer_payloads(
    rows: List[Dict[str, Any]],
    *,
    get_blob: Callable[[Dict[str, Any]], Optional[bytes]],
    mx: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    from utils.topic_practice_state import topic_audio_key

    payloads: List[Dict[str, Any]] = []
    total_bytes = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        q_idx = int(row.get("question_index") or 0)
        topic_id = str(row.get("topic_id") or "")
        question_id = str(row.get("question_id") or "")
        q_idx = int(row.get("question_index") or 0)
        audio_key = str(row.get("audio_key") or "") or topic_audio_key(
            topic_id, question_id, q_idx
        )
        blob = get_blob(row)
        nbytes = recording_byte_length(blob) if blob else int(row.get("audio_len") or 0)
        mime = str(row.get("mime_type") or "").strip()
        if blob and mx is not None and not mime:
            from utils.speech_recording import resolve_mime_for_analysis

            mime = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
        payloads.append(
            {
                "question_index": q_idx,
                "question_id": question_id,
                "question_text": str(row.get("question_text") or ""),
                "question_label": _question_label(q_idx),
                "audio_key": audio_key,
                "audio_bytes": blob,
                "audio_len": nbytes,
                "mime_type": mime,
                "row": row,
            }
        )
        if blob:
            total_bytes += len(blob)
    return payloads, total_bytes


def _apply_restored_to_rows(
    topic_id: str,
    topic_title: str,
    payloads: List[Dict[str, Any]],
    restored_list: List[Dict[str, Any]],
) -> None:
    from data.topic_practice_questions import get_topic_question
    from utils.topic_practice_state import apply_topic_completed_result

    by_idx: Dict[int, Dict[str, Any]] = {}
    for item in restored_list:
        if not isinstance(item, dict):
            continue
        idx = item.get("question_index")
        if idx is None:
            lbl = str(item.get("question_label") or "")
            m = re.match(r"Q(\d+)", lbl, re.I)
            idx = int(m.group(1)) - 1 if m else -1
        if int(idx) >= 0:
            by_idx[int(idx)] = item

    for payload in payloads:
        row = payload.get("row")
        if not isinstance(row, dict):
            continue
        q_idx = int(payload.get("question_index") or 0)
        item = by_idx.get(q_idx, {})
        transcript = str(item.get("transcript") or "").strip()
        lang = str(item.get("language_status") or "english").lower()
        result: Dict[str, Any] = {
            "analysis_status": "completed",
            "diagnosis_status": "ok" if lang == "english" else lang,
            "transcript": transcript,
            "restored_transcript": transcript,
            "language_status": lang,
            "topic_report_batch": True,
            "source_audio_size_bytes": int(payload.get("audio_len") or 0),
        }
        if lang in ("non_english", "unclear", "no_speech", "no_audio"):
            result["diagnosis_status"] = lang
        question = get_topic_question(topic_id, q_idx) or {
            "question_id": payload.get("question_id"),
            "question_en": payload.get("question_text") or "",
        }
        apply_topic_completed_result(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=q_idx,
            question=question,
            audio_key=str(payload.get("audio_key") or ""),
            result=result,
        )


def _log_failure(path: str, error: str) -> None:
    empty = bool(error and "비어" in error)
    cat = classify_ai_error(error, empty_response=empty)
    short = analysis_error_short(error)[:80]
    _diag_log(
        f"gemini_call_failed | path={path} | category={cat} | short_error={short!r}"
    )
    log_ai_pending_reason(
        error_message=error or "unknown",
        question_index=-1,
        mode="topic_practice",
        category=cat,
        empty_response=empty,
    )


def run_topic_mini_report_analysis(
    saved_answers: List[Dict[str, Any]],
    topic_info: Dict[str, Any],
    api_key: str,
    *,
    difficulty: int = 5,
    mx: Optional[Dict[str, Any]] = None,
    get_blob: Optional[Callable[[Dict[str, Any]], Optional[bytes]]] = None,
    consume_daily_slot: bool = True,
    from_retry: bool = False,
) -> Dict[str, Any]:
    """
    Build a topic report with at most one Gemini call.

    Path A (text_only): >=2 meaningful transcripts → text-only report, no audio.
    Path B (one_call_audio_batch): otherwise → one multimodal call with 3 audios.
    """
    from utils.topic_practice_state import get_topic_answer_blob

    topic_id = str(topic_info.get("topic_id") or "")
    topic_title = str(topic_info.get("topic_title") or "주제")
    topic_category = str(
        topic_info.get("topic_category") or topic_info.get("category") or ""
    )
    blob_fn = get_blob or get_topic_answer_blob

    payloads, total_bytes = _prepare_saved_answer_payloads(
        saved_answers, get_blob=blob_fn, mx=mx
    )

    _diag_log(
        f"clicked | saved_answers={len(payloads)} | topic_id={topic_id or '—'}"
    )

    if len(payloads) < 3:
        return _result_failed("저장된 답변이 3개가 아닙니다. 각 문항을 녹음해 주세요.")

    meaningful: List[Tuple[int, str]] = []
    for p in payloads:
        row = p.get("row")
        if isinstance(row, dict):
            tr = get_meaningful_transcript(row)
            if tr:
                meaningful.append((int(p.get("question_index") or 0), tr))

    _diag_log(f"transcript_count={len(meaningful)}")

    missing_audio = any(not p.get("audio_bytes") for p in payloads)
    if missing_audio and len(meaningful) < MIN_MEANINGFUL_TRANSCRIPTS_FOR_TEXT_ONLY:
        return _result_failed(
            "일부 답변 녹음을 찾을 수 없어요. 해당 문항을 다시 녹음해 주세요."
        )

    oversized = total_bytes > MAX_TOPIC_MINI_TOTAL_AUDIO_BYTES or any(
        int(p.get("audio_len") or 0) > MAX_TOPIC_MINI_PER_AUDIO_BYTES for p in payloads
    )
    if oversized and len(meaningful) < MIN_MEANINGFUL_TRANSCRIPTS_FOR_TEXT_ONLY:
        return _result_failed(
            "녹음 파일이 너무 커서 한 번에 분석할 수 없어요. "
            "각 답변을 조금 짧게 다시 녹음해 주세요."
        )

    if ALLOW_TOPIC_SEQUENTIAL_ANALYSIS and not TOPIC_MINI_REPORT_ONE_CALL_ONLY:
        return _run_sequential_analysis_legacy(
            payloads, topic_info, api_key, difficulty=difficulty, mx=mx
        )

    if not api_key:
        return _result_pending_retry(reason="no_api_key", saved_count=len(payloads))

    from services.evaluation_service import _GEMINI_LOCK, _LOCK_ACQUIRE_TIMEOUT

    ai_diag.set_diag_context(
        {
            "caller": "topic_mini_report_analysis.run_topic_mini_report_analysis",
            "mock_mode": "topic_practice",
            "topic_id": topic_id,
        }
    )

    acquired = _GEMINI_LOCK.acquire(timeout=_LOCK_ACQUIRE_TIMEOUT)
    if not acquired:
        log_ai_pending_reason(
            error_message="분석 대기열 타임아웃",
            question_index=-1,
            mode="topic_practice",
            audio_bytes_len=total_bytes,
        )
        return _result_pending_retry(reason="lock_timeout", saved_count=len(payloads))

    # Transcript-first: never send raw answer audio for active topic report evaluation.
    if len(meaningful) < 1:
        return _result_pending_retry(
            reason="insufficient_transcripts",
            saved_count=len(payloads),
        )
    use_text_only = True
    path = "text_only"

    try:
        if consume_daily_slot and not from_retry:
            from utils.daily_ai_usage import (
                is_daily_ai_limit_enabled,
                try_consume_daily_ai_slot,
            )

            if is_daily_ai_limit_enabled():
                ok, msg = try_consume_daily_ai_slot()
                if not ok:
                    return _result_failed(msg)

        report, err = _path_text_only(
            payloads,
            topic_title=topic_title,
            topic_category=topic_category,
            meaningful=meaningful,
            api_key=api_key,
        )
        raw_parsed = None
    finally:
        _GEMINI_LOCK.release()

    if report and not err and is_real_topic_ai_report(report):
        if path == "one_call_audio_batch" and raw_parsed:
            restored = report.get("restored_transcripts") or []
            if restored:
                _apply_restored_to_rows(topic_id, topic_title, payloads, restored)
        _diag_log("report_status=completed")
        return _result_completed(report)

    _log_failure(path, err or "gemini_failed")
    return _result_pending_retry(
        reason=err or "gemini_failed",
        saved_count=len(payloads),
    )


# Legacy helpers — not used as final report
def build_local_topic_mini_report_fallback(
    topic_title: str,
    saved_answers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Dev/optional only — must NOT set topic_report_status=completed."""
    _diag_log("local_fallback_built | not_used_as_final_report=True")
    ordered = sorted(
        [a for a in saved_answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    )
    save_lines: List[str] = []
    for row in ordered:
        qn = int(row.get("question_index") or 0) + 1
        nbytes = int(row.get("audio_len") or 0)
        save_lines.append(f"Q{qn} 저장 완료" + (f" · {nbytes:,} bytes" if nbytes else ""))
    return {
        "topic_title": topic_title,
        "flow_summary": f"「{topic_title}」 — 임시 연습 가이드 (AI 리포트 아님)",
        "local_fallback": True,
        "report_source": "local_fallback",
        "save_status_lines": save_lines,
    }


def _run_sequential_analysis_legacy(
    payloads: List[Dict[str, Any]],
    topic_info: Dict[str, Any],
    api_key: str,
    *,
    difficulty: int,
    mx: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Dev-only: sequential per-question Gemini (3 calls) — disabled by default."""
    from services.evaluation_service import analyze_audio_with_retry
    from utils.topic_practice_state import (
        apply_topic_completed_result,
        apply_topic_pending_result,
    )

    topic_id = str(topic_info.get("topic_id") or "")
    topic_title = str(topic_info.get("topic_title") or "")
    any_pending = False

    for payload in payloads:
        blob = payload.get("audio_bytes")
        if not blob:
            continue
        q_idx = int(payload.get("question_index") or 0)
        from data.topic_practice_questions import get_topic_question

        question = get_topic_question(topic_id, q_idx) or {}
        mime = payload.get("mime_type") or ""
        result, last_error, attempts = analyze_audio_with_retry(
            bytes(blob),
            str(payload.get("question_text") or ""),
            api_key,
            difficulty,
            mime_guess=mime,
            diag={
                "caller": "topic_mini_report.sequential_legacy",
                "question_index": q_idx,
            },
        )
        if not result or last_error:
            any_pending = True
            apply_topic_pending_result(
                topic_id=topic_id,
                topic_title=topic_title,
                question_index=q_idx,
                question=question,
                audio_key=str(payload.get("audio_key") or ""),
                error_message=last_error or "AI 분석 실패",
                attempts=attempts,
            )
            continue
        apply_topic_completed_result(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=q_idx,
            question=question,
            audio_key=str(payload.get("audio_key") or ""),
            result=result,
        )

    if any_pending:
        return _result_pending_retry(
            reason="sequential_partial_failure",
            saved_count=len(payloads),
        )
    return _result_pending_retry(reason="sequential_disabled_use_one_call", saved_count=3)
