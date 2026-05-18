"""Recording presence vs speech recognition outcomes (no Gemini/scoring changes)."""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from services.evaluation.audio_mime import resolve_audio_mime
from utils.audio_pipeline_diag import trust_result_label
from utils.audio_utils import mime_from_audio_format
from utils.language_detection import (
    detect_language_mismatch,
    language_mismatch_body,
    language_mismatch_title,
    transcript_for_language_check,
)
from utils.text_utils import is_real_speech_transcript

# Below this size we treat the browser/recorder as not having saved real audio.
MIN_RECORDED_AUDIO_BYTES = 3000


def recording_byte_length(blob: Any) -> int:
    if not blob or not isinstance(blob, (bytes, bytearray)):
        return 0
    return len(blob)


def has_substantial_recording(blob: Any) -> bool:
    return recording_byte_length(blob) >= MIN_RECORDED_AUDIO_BYTES


def analysis_has_real_transcript(result: Optional[dict]) -> bool:
    if not isinstance(result, dict):
        return False
    if str(result.get("diagnosis_status") or "").lower() in (
        "needs_review",
        "non_english",
        "language_mismatch",
    ):
        return False
    if str(result.get("analysis_status") or "").lower() == "non_english":
        return False
    if bool(result.get("no_speech_detected")):
        return False
    if str(result.get("diagnosis_status") or "").lower() == "no_speech":
        return False
    raw = (result.get("transcript") or "").strip()
    return bool(raw) and is_real_speech_transcript(raw)


def classify_post_analysis_issue(blob: Any, result: Optional[dict]) -> str:
    """``ok`` | ``no_audio`` | ``non_english`` | ``needs_review`` | ``unclear_speech``."""
    if not has_substantial_recording(blob):
        return "no_audio"
    if isinstance(result, dict):
        diagnosis = str(result.get("diagnosis_status") or "").lower()
        if diagnosis in ("non_english", "language_mismatch"):
            return "non_english"
        lang_text = transcript_for_language_check(result)
        if detect_language_mismatch(lang_text):
            return "non_english"
        if diagnosis == "needs_review":
            return "needs_review"
    if analysis_has_real_transcript(result):
        return "ok"
    return "unclear_speech"


def classify_pre_analysis_blob(blob: Any) -> str:
    """``no_audio`` when bytes are missing/tiny; else ready for Gemini."""
    if not has_substantial_recording(blob):
        return "no_audio"
    return "ok"


def resolve_mime_for_analysis(
    blob: Any,
    *,
    mx: Optional[dict] = None,
    audio_key: str = "",
    result: Optional[dict] = None,
) -> str:
    """MIME passed to Gemini — recorder hint first, then sniffed bytes."""
    if isinstance(result, dict):
        mime = (result.get("audio_mime_guess") or "").strip()
        if mime:
            return mime
    if mx and audio_key:
        by_key = mx.get("recording_mime_by_key")
        if isinstance(by_key, dict):
            stored = (by_key.get(audio_key) or "").strip()
            if stored:
                return resolve_audio_mime(bytes(blob or b""), stored)
    if blob:
        return resolve_audio_mime(bytes(blob))
    return ""


def resolve_mime_for_debug(
    blob: Any,
    *,
    mx: Optional[dict] = None,
    audio_key: str = "",
    result: Optional[dict] = None,
) -> str:
    return resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key, result=result)


def speech_issue_copy(issue: str) -> tuple[str, str, str]:
    """Eyebrow, title, body for no-audio vs unclear-speech cards."""
    if issue == "no_audio":
        return (
            "녹음 저장 실패",
            "녹음이 제대로 저장되지 않았어요",
            "마이크 권한을 확인하고, 조용한 환경에서 3초 이상 다시 녹음해 주세요.",
        )
    if issue == "unclear_speech":
        return (
            "말소리 인식 어려움",
            "말소리가 정확히 인식되지 않았어요",
            "녹음은 저장되었지만, AI가 답변을 충분히 읽지 못했어요. "
            "조금 더 또렷하게 다시 말하거나, 저장하고 다음 문항으로 넘어갈 수 있어요.",
        )
    if issue == "needs_review":
        return (
            "인식 검토 필요",
            "답변 일부가 불명확하게 인식되었어요",
            "녹음은 저장되었지만, AI가 답변 전체를 확신 있게 읽지 못했어요. "
            "조금 더 또렷하게 다시 말하거나, 같은 녹음으로 다시 분석할 수 있어요.",
        )
    if issue == "non_english":
        kind = "korean"
        return (
            "언어 안내",
            language_mismatch_title(kind),
            language_mismatch_body(kind),
        )
    return (
        "음성 미감지",
        "음성이 감지되지 않았어요 🙏",
        "이번 답변에서는 인식된 발화가 없습니다. 마이크가 켜져 있는지 확인하고 "
        "다시 한 번 또렷한 목소리로 답변해 보세요.",
    )


def build_recording_debug_lines(
    mx: dict,
    audio_key: str,
    result: Optional[dict],
    *,
    q_index: Optional[int] = None,
    blob: Any = None,
    gemini_error: str = "",
) -> List[str]:
    """Developer-only lines for no-speech / recovery cards (no secrets)."""
    res = result if isinstance(result, dict) else {}
    blob_len = recording_byte_length(blob)
    if blob_len == 0 and mx:
        saved = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
        blob_len = recording_byte_length(saved)
    mime = resolve_mime_for_debug(blob, mx=mx, audio_key=audio_key, result=res)
    tx_len = len((res.get("transcript") or "").strip())
    status = (
        str(res.get("analysis_status") or res.get("diagnosis_status") or mx.get("analysis_status") or "")
        or "—"
    )
    trust = trust_result_label(res)
    err_short = " ".join((gemini_error or res.get("error") or "").split())[:120]
    q_line = f"question_index: {q_index}" if q_index is not None else ""
    rec_keys = sorted((mx.get("recordings") or {}).keys()) if isinstance(mx.get("recordings"), dict) else []
    state_bits = [
        f"audio_bytes_in_mx: {'yes' if mx.get('audio_bytes') else 'no'}",
        f"recording_keys: {len(rec_keys)}",
    ]
    try:
        import streamlit as st

        if st.session_state.get("recording_timer_active"):
            state_bits.append("session_timer_active: yes")
    except Exception:
        pass
    lines = [
        f"audio_bytes: {blob_len}",
        f"mime_type: {mime or '—'}",
        f"transcript_len: {tx_len}",
        f"analysis_status: {status}",
        f"trust_gate_result: {trust}",
    ]
    if err_short:
        lines.append(f"gemini_error: {err_short}")
    if q_line:
        lines.append(q_line)
    lines.extend(state_bits)
    return lines


def render_language_mismatch_preview(result: Optional[dict]) -> None:
    """Optional short transcript preview on non-English cards."""
    import streamlit as st

    if not isinstance(result, dict):
        return
    preview = (result.get("non_english_preview") or "").strip()
    if not preview:
        preview = transcript_for_language_check(result)
    preview = " ".join(preview.split())
    if len(preview) < 4:
        return
    if len(preview) > 120:
        preview = preview[:119] + "…"
    st.markdown(
        f'<p class="mx-rh-transcript mx-rh-transcript--preview">'
        f"인식된 일부 내용:<br/>"
        f'"{html.escape(preview)}"</p>',
        unsafe_allow_html=True,
    )


def render_recording_debug_block(
    mx: dict,
    audio_key: str,
    result: Optional[dict],
    *,
    q_index: Optional[int] = None,
    blob: Any = None,
    gemini_error: str = "",
) -> None:
    """Audio pipeline diagnostics — hidden from students unless ``show_dev_debug``."""
    import streamlit as st

    if not st.session_state.get("show_dev_debug", False):
        return

    lines = build_recording_debug_lines(
        mx,
        audio_key,
        result,
        q_index=q_index,
        blob=blob,
        gemini_error=gemini_error,
    )
    with st.expander("개발 확인", expanded=False):
        st.code("\n".join(lines), language=None)
