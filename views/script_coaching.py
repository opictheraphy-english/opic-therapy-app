"""Script Coaching — written OPIc script diagnose (Stage 1) + upgrade (Stage 2)."""

from __future__ import annotations

import base64
import html
import logging
import time
from typing import Any, Dict, List, Tuple

import streamlit as st

from components.score_donut_bars import render_score_donut_bars_html
from components.smart_feedback import (
    render_alternative_expressions,
    render_grammar_corrections,
)
from components.topbar import render_top_bar
from utils.analysis_request_guard import (
    button_state as guard_button_state,
    can_request as guard_can_request,
    clear_guard as guard_clear_guard,
    clear_stale_in_flight as guard_clear_stale_in_flight,
    key_in_flight as guard_key_in_flight,
    register_failure as guard_register_failure,
    reset_guard as guard_reset_guard,
    set_in_flight as guard_set_in_flight,
)

logger = logging.getLogger(__name__)

_GUARD_ENTITY_ID = "default"
_DIAGNOSE_GUARD_PREFIX = "script_coaching_diagnose"
_UPGRADE_GUARD_PREFIX = "script_coaching_upgrade"
_KEY_UPGRADE_ACTIVE_BUTTON = "script_coaching_upgrade_active_button_key"

_GUARD_MAX_ATTEMPTS = 4
_GUARD_STALE_SEC = 55
_GUARD_COOLDOWN_BASE = 45
_GUARD_COOLDOWN_STEP = 15
_GUARD_COOLDOWN_MAX = 90

_SC_DIAGNOSE_LABELS: Dict[str, Any] = {
    "idle": "진단받기",
    "in_flight": "진단 중…",
    "cooldown": lambda rem: f"{rem}초 후 다시",
    "maxed": "잠시 후 다시 시도",
}
_SC_UPGRADE_GUARD_LABELS: Dict[str, Any] = {
    "idle": "업그레이드",
    "in_flight": "업그레이드 중…",
    "cooldown": lambda rem: f"{rem}초 후 다시",
    "maxed": "잠시 후 다시 시도",
}

_KEY_STEP = "script_coaching_step"
_KEY_QUESTION_EN = "script_coaching_question_en"
_KEY_SCRIPT_TEXT = "script_coaching_script_text"
_KEY_DIAGNOSE_RESULT = "script_coaching_diagnose_result"
_KEY_UPGRADE_RESULT = "script_coaching_upgrade_result"
_KEY_CLEAR_INPUTS = "script_coaching_clear_inputs"
_KEY_MIC_OUTPUT = "script_coaching_mic_output"
_KEY_STT_NOTICE = "script_coaching_stt_notice"

_SCORE_LABELS: Dict[str, str] = {
    "response_amount": "분량",
    "vocabulary": "어휘",
    "grammar": "문법",
    "context": "맥락",
    "structure": "구조",
}


def clear_script_coaching_session() -> None:
    """Clear script coaching UI state (portal reset / leave flow)."""
    _reset_all_analysis_guards()
    for k in (
        _KEY_STEP,
        _KEY_QUESTION_EN,
        _KEY_SCRIPT_TEXT,
        _KEY_DIAGNOSE_RESULT,
        _KEY_UPGRADE_RESULT,
        _KEY_CLEAR_INPUTS,
        _KEY_MIC_OUTPUT,
        _KEY_STT_NOTICE,
    ):
        st.session_state.pop(k, None)


def _clear_script_coaching_mic_cache() -> None:
    st.session_state.pop(_KEY_MIC_OUTPUT, None)
    st.session_state.pop(_KEY_STT_NOTICE, None)


def _reset_diagnose_guard() -> None:
    guard_reset_guard(st.session_state, _DIAGNOSE_GUARD_PREFIX)


def _reset_upgrade_guard() -> None:
    st.session_state.pop(_KEY_UPGRADE_ACTIVE_BUTTON, None)
    guard_reset_guard(st.session_state, _UPGRADE_GUARD_PREFIX)


def _reset_all_analysis_guards() -> None:
    _reset_diagnose_guard()
    _reset_upgrade_guard()


def _diagnose_button_state() -> Tuple[bool, str]:
    guard_clear_stale_in_flight(
        st.session_state,
        _DIAGNOSE_GUARD_PREFIX,
        stale_sec=_GUARD_STALE_SEC,
    )
    return guard_button_state(
        st.session_state,
        _DIAGNOSE_GUARD_PREFIX,
        _GUARD_ENTITY_ID,
        labels=_SC_DIAGNOSE_LABELS,
        max_attempts=_GUARD_MAX_ATTEMPTS,
        stale_sec=_GUARD_STALE_SEC,
    )


def _upgrade_guard_disabled() -> Tuple[bool, str]:
    guard_clear_stale_in_flight(
        st.session_state,
        _UPGRADE_GUARD_PREFIX,
        stale_sec=_GUARD_STALE_SEC,
    )
    return guard_button_state(
        st.session_state,
        _UPGRADE_GUARD_PREFIX,
        _GUARD_ENTITY_ID,
        labels=_SC_UPGRADE_GUARD_LABELS,
        max_attempts=_GUARD_MAX_ATTEMPTS,
        stale_sec=_GUARD_STALE_SEC,
    )


def _upgrade_button_state(button_key: str, idle_label: str) -> Tuple[bool, str]:
    disabled, guard_label = _upgrade_guard_disabled()
    if not disabled:
        return False, idle_label
    if (
        st.session_state.get(guard_key_in_flight(_UPGRADE_GUARD_PREFIX))
        and str(st.session_state.get(_KEY_UPGRADE_ACTIVE_BUTTON) or "") == button_key
    ):
        return True, "업그레이드 중…"
    if guard_label != _SC_UPGRADE_GUARD_LABELS["idle"]:
        return True, guard_label
    return True, idle_label


def _failure_category(result: Dict[str, Any]) -> str:
    cat = str(result.get("error_category") or "").strip()
    return cat or "api_error"


def _run_diagnose_guarded(question_en: str, script_text: str) -> None:
    allowed, block_msg = guard_can_request(
        st.session_state,
        _DIAGNOSE_GUARD_PREFIX,
        _GUARD_ENTITY_ID,
        max_attempts=_GUARD_MAX_ATTEMPTS,
        stale_sec=_GUARD_STALE_SEC,
    )
    if not allowed:
        if block_msg:
            st.warning(block_msg)
        return

    from services.script_coaching_diagnose_analysis import diagnose_script

    q = str(question_en or "").strip()
    s = str(script_text or "").strip()
    result: Dict[str, Any]
    guard_set_in_flight(st.session_state, _DIAGNOSE_GUARD_PREFIX, True)
    try:
        with st.spinner("AI가 스크립트를 진단하고 있어요…"):
            result = diagnose_script(q, s)
    except Exception as exc:
        try:
            logger.exception("[SCRIPT_COACHING_DIAGNOSE] analyze_failed: %s", exc)
        except Exception:
            pass
        result = {
            "ok": False,
            "error_category": "exception",
            "error_message": "진단 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
        }
    finally:
        guard_set_in_flight(st.session_state, _DIAGNOSE_GUARD_PREFIX, False)

    if result.get("ok"):
        result = _merge_user_script_fields(result)
        guard_clear_guard(st.session_state, _DIAGNOSE_GUARD_PREFIX, _GUARD_ENTITY_ID)
        _reset_upgrade_guard()
    else:
        guard_register_failure(
            st.session_state,
            _DIAGNOSE_GUARD_PREFIX,
            _GUARD_ENTITY_ID,
            _failure_category(result),
            base_cooldown=_GUARD_COOLDOWN_BASE,
            step=_GUARD_COOLDOWN_STEP,
            max_cooldown=_GUARD_COOLDOWN_MAX,
        )

    st.session_state[_KEY_DIAGNOSE_RESULT] = result
    if result.get("ok"):
        st.session_state[_KEY_STEP] = "result"
        try:
            from utils.history_sync import save_script_diagnose

            save_script_diagnose(result, question=q, sig=str(time.time()))
        except Exception:
            pass
    st.rerun()


def _ensure_defaults() -> None:
    if st.session_state.pop(_KEY_CLEAR_INPUTS, False):
        st.session_state[_KEY_QUESTION_EN] = ""
        st.session_state[_KEY_SCRIPT_TEXT] = ""
        _clear_script_coaching_mic_cache()
        _reset_all_analysis_guards()
    if _KEY_STEP not in st.session_state:
        st.session_state[_KEY_STEP] = "input"
    if _KEY_QUESTION_EN not in st.session_state:
        st.session_state[_KEY_QUESTION_EN] = ""
    if _KEY_SCRIPT_TEXT not in st.session_state:
        st.session_state[_KEY_SCRIPT_TEXT] = ""


def _render_stt_notice() -> None:
    msg = str(st.session_state.pop(_KEY_STT_NOTICE, "") or "").strip()
    if msg:
        st.warning(msg)


def _set_stt_notice(msg: str) -> None:
    text = str(msg or "").strip()
    if text:
        st.session_state[_KEY_STT_NOTICE] = text


def _sc_mime_from_mic_dict(mic_dict: Dict[str, Any], audio_bytes: bytes) -> str:
    for key in ("mime_type", "mimeType", "type"):
        val = str(mic_dict.get(key) or "").strip()
        if val:
            if "/" in val:
                return val
            from utils.audio_utils import mime_from_audio_format

            return mime_from_audio_format(val)
    fmt = str(mic_dict.get("format") or "").strip()
    if fmt:
        from utils.audio_utils import mime_from_audio_format

        return mime_from_audio_format(fmt)
    from services.evaluation.audio_mime import resolve_audio_mime

    return resolve_audio_mime(audio_bytes, "")


def _coerce_sc_mic_payload_to_bytes(raw: Any) -> Tuple[bytes, str]:
    if raw is None:
        return b"", "missing"
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw), ""
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return b"", "empty_string"
        try:
            return base64.b64decode(text, validate=False), ""
        except Exception:
            logger.debug("[SCRIPT_COACHING_AUDIO] base64_decode_failed", exc_info=True)
            return b"", "base64_decode_failed"
    if isinstance(raw, list):
        try:
            return bytes(int(x) for x in raw), ""
        except (TypeError, ValueError):
            return b"", "list_int_convert_failed"
    try:
        return bytes(raw), ""
    except (TypeError, ValueError):
        return b"", "unsupported_type"


def _extract_script_coaching_audio_bytes(
    mic_result: Any,
) -> Tuple[bytes, str]:
    """Normalize streamlit_mic_recorder output; fall back to session cache when just_once clears return."""
    sources: List[Any] = []
    if mic_result is not None:
        sources.append(mic_result)
    cached = st.session_state.get(_KEY_MIC_OUTPUT)
    if cached is not None and cached is not mic_result:
        sources.append(cached)

    last_fail = "no_payload"
    for payload in sources:
        if isinstance(payload, (bytes, bytearray)):
            blob = bytes(payload)
            if blob:
                return blob, "audio/webm"
            last_fail = "empty_bytes"
            continue
        if not isinstance(payload, dict):
            last_fail = "unsupported_type"
            continue
        for key in ("bytes", "audio", "blob", "data", "audio_bytes"):
            if key not in payload:
                continue
            blob, fail = _coerce_sc_mic_payload_to_bytes(payload.get(key))
            if fail:
                last_fail = fail
                continue
            if blob:
                return blob, _sc_mime_from_mic_dict(payload, blob)
        last_fail = "dict_no_audio_field"

    try:
        logger.warning("[SCRIPT_COACHING_AUDIO_EXTRACT] failed category=%s", last_fail)
    except Exception:
        pass
    return b"", ""


def _stt_user_message(stt: Dict[str, Any]) -> str:
    cat = str(stt.get("error_category") or "").strip()
    if cat == "empty_audio":
        return "소리가 녹음되지 않았어요. 다시 시도해 주세요."
    if cat == "timeout":
        return "변환이 지연됐어요. 다시 시도해 주세요."
    return "음성 변환에 실패했어요. 다시 시도해 주세요."


def _append_transcript_to_script(transcript: str) -> None:
    new_text = str(transcript or "").strip()
    if not new_text:
        return
    existing = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    if existing:
        st.session_state[_KEY_SCRIPT_TEXT] = f"{existing} {new_text}".strip()
    else:
        st.session_state[_KEY_SCRIPT_TEXT] = new_text


def _stash_script_coaching_mic_result(mic_result: Any) -> None:
    """Cache mic capture; STT runs on the next rerun before text_area renders."""
    if mic_result is None:
        return
    st.session_state[_KEY_MIC_OUTPUT] = mic_result
    st.rerun()


def _process_pending_script_coaching_stt() -> None:
    """Run STT on cached mic audio and append transcript — call only before text_area widgets."""
    mic_result = st.session_state.get(_KEY_MIC_OUTPUT)
    if mic_result is None:
        return

    question_en = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    audio_bytes, mime_type = _extract_script_coaching_audio_bytes(mic_result)
    if len(audio_bytes) <= 0:
        _set_stt_notice("소리가 녹음되지 않았어요. 다시 시도해 주세요.")
        st.session_state.pop(_KEY_MIC_OUTPUT, None)
        st.rerun()

    from services.stt_service import transcribe_answer_audio

    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"
    with st.spinner("음성을 텍스트로 변환하고 있어요…"):
        stt = transcribe_answer_audio(
            audio_bytes,
            mime_type=resolved_mime,
            language_hint="en",
            question_text=question_en,
            mode="script_coaching",
            question_id="script_coaching_draft",
        )

    transcript = str(stt.get("transcript") or stt.get("text") or "").strip()
    st.session_state.pop(_KEY_MIC_OUTPUT, None)
    if stt.get("ok") and transcript:
        _append_transcript_to_script(transcript)
        st.rerun()

    if stt.get("ok") and not transcript:
        _set_stt_notice("말씀 내용을 인식하지 못했어요. 다시 시도해 주세요.")
    else:
        _set_stt_notice(_stt_user_message(stt if isinstance(stt, dict) else {}))
    st.rerun()


def _render_input_form() -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_stt_notice()

    # STT + script text update must run before text_area(key=_KEY_SCRIPT_TEXT) is instantiated.
    if st.session_state.get(_KEY_MIC_OUTPUT) is not None:
        _process_pending_script_coaching_stt()

    st.markdown(
        """
        <section class="continue-card continue-card--start mx-mode-card" role="region">
          <div class="cc-title">스크립트 첨삭</div>
          <div class="cc-meta">영어 질문과 내가 쓴 답변 스크립트를 입력하면 AI가 등급과 첨삭 피드백을 알려줘요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    question_en = st.text_area(
        "질문 (영어)",
        key=_KEY_QUESTION_EN,
        height=100,
        placeholder="예: What kind of music do you usually listen to?",
    )
    script_text = st.text_area(
        "내 답변 스크립트 (영어)",
        key=_KEY_SCRIPT_TEXT,
        height=200,
        placeholder="여기에 답변 스크립트를 영어로 입력해 주세요.",
    )

    from streamlit_mic_recorder import mic_recorder

    mic_result = mic_recorder(
        start_prompt="🎤 말로 입력",
        stop_prompt="■ 변환하기",
        key=None,
        use_container_width=True,
        just_once=True,
    )
    st.markdown(
        '<p class="ds-muted" style="font-size:12px;margin:4px 0 12px 0;">'
        "말한 내용이 위 칸에 이어서 채워져요. 변환 후 자유롭게 수정하세요."
        "</p>",
        unsafe_allow_html=True,
    )

    if mic_result is not None:
        _stash_script_coaching_mic_result(mic_result)

    diag_disabled, diag_label = _diagnose_button_state()
    if st.button(
        diag_label,
        type="primary",
        use_container_width=True,
        key="script_coaching_run_diagnose",
        disabled=diag_disabled,
    ):
        _run_diagnose_guarded(question_en, script_text)


def _sc_card(title: str, body_html: str) -> None:
    """Render a script-report section inside the boxed card style."""
    st.markdown(
        f'<section class="sc-report-card" role="region">'
        f'<div class="sc-card-title">{html.escape(title)}</div>'
        f'<div class="sc-card-body">{body_html}</div>'
        f"</section>",
        unsafe_allow_html=True,
    )


def _merge_user_script_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach session question/script to a result dict for save & display (no AI changes)."""
    if not isinstance(result, dict):
        return result
    merged = dict(result)
    merged["question_en"] = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    merged["original_script"] = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    return merged


def _resolve_original_script(report: Dict[str, Any]) -> str:
    """Original script from saved report fields or live session."""
    if isinstance(report, dict):
        saved = str(report.get("original_script") or "").strip()
        if saved:
            return saved
    return str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()


def _sc_bullets_html(items: Any) -> str:
    if not isinstance(items, (list, tuple)):
        return ""
    lis = "".join(
        f"<li>{html.escape(str(x))}</li>" for x in items if str(x).strip()
    )
    return f"<ul>{lis}</ul>" if lis else ""


def _run_upgrade(
    current_level: str,
    target_level: str = "",
    *,
    button_key: str = "",
) -> None:
    allowed, block_msg = guard_can_request(
        st.session_state,
        _UPGRADE_GUARD_PREFIX,
        _GUARD_ENTITY_ID,
        max_attempts=_GUARD_MAX_ATTEMPTS,
        stale_sec=_GUARD_STALE_SEC,
    )
    if not allowed:
        if block_msg:
            st.warning(block_msg)
        return

    from services.script_coaching_upgrade_analysis import upgrade_script

    question_en = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    script_text = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    if button_key:
        st.session_state[_KEY_UPGRADE_ACTIVE_BUTTON] = button_key
    result: Dict[str, Any]
    guard_set_in_flight(st.session_state, _UPGRADE_GUARD_PREFIX, True)
    try:
        with st.spinner("AI가 스크립트를 변환하고 있어요…"):
            result = upgrade_script(
                question_en,
                script_text,
                current_level,
                target_level=target_level,
                question_ko="",
            )
    except Exception as exc:
        try:
            logger.exception("[SCRIPT_COACHING_UPGRADE] analyze_failed: %s", exc)
        except Exception:
            pass
        result = {
            "ok": False,
            "error_category": "exception",
            "error_message": "변환 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
        }
    finally:
        guard_set_in_flight(st.session_state, _UPGRADE_GUARD_PREFIX, False)
        st.session_state.pop(_KEY_UPGRADE_ACTIVE_BUTTON, None)

    if result.get("ok"):
        result = _merge_user_script_fields(result)
        guard_clear_guard(st.session_state, _UPGRADE_GUARD_PREFIX, _GUARD_ENTITY_ID)
    else:
        guard_register_failure(
            st.session_state,
            _UPGRADE_GUARD_PREFIX,
            _GUARD_ENTITY_ID,
            _failure_category(result),
            base_cooldown=_GUARD_COOLDOWN_BASE,
            step=_GUARD_COOLDOWN_STEP,
            max_cooldown=_GUARD_COOLDOWN_MAX,
        )

    st.session_state[_KEY_UPGRADE_RESULT] = result
    if result.get("ok"):
        st.session_state[_KEY_STEP] = "upgrade_result"
        try:
            from utils.history_sync import save_script_upgrade

            save_script_upgrade(result, sig=str(time.time()))
        except Exception:
            pass
    st.rerun()


def _render_upgrade_section(report: Dict[str, Any]) -> None:
    from services.script_coaching_upgrade_analysis import upgrade_options_for

    overall_level = str(report.get("overall_level") or "").strip()
    opts = upgrade_options_for(overall_level)
    mode = str(opts.get("mode") or "").strip().lower()
    one_step = opts.get("one_step")
    two_step = opts.get("two_step")

    upgrade_result = st.session_state.get(_KEY_UPGRADE_RESULT)
    if isinstance(upgrade_result, dict) and not upgrade_result.get("ok"):
        msg = str(upgrade_result.get("error_message") or "").strip()
        if msg:
            st.error(msg)

    _sc_card(
        "더 높은 등급으로 다시 써 보기",
        "<p>진단 등급을 기준으로 AI가 스크립트를 목표 등급 수준으로 변환해 줍니다.</p>",
    )

    if mode == "polish":
        _sc_card(
            "이미 최상위 등급이에요",
            "<p>표현을 한 단계 더 다듬은 보완본을 만들어 드릴까요?</p>",
        )
        polish_key = "script_coaching_upgrade_polish"
        polish_idle = "보완본 받기"
        polish_disabled, polish_label = _upgrade_button_state(polish_key, polish_idle)
        if st.button(
            polish_label,
            type="primary",
            use_container_width=True,
            key=polish_key,
            disabled=polish_disabled,
        ):
            _run_upgrade(overall_level, target_level="", button_key=polish_key)
        return

    if mode != "upgrade" or not one_step:
        return

    if two_step:
        col1, col2 = st.columns(2)
        one_key = "script_coaching_upgrade_one_step"
        one_idle = f"한 단계 업그레이드 ({one_step})"
        two_key = "script_coaching_upgrade_two_step"
        two_idle = f"두 단계 업그레이드 ({two_step})"
        with col1:
            one_disabled, one_label = _upgrade_button_state(one_key, one_idle)
            if st.button(
                one_label,
                type="primary",
                use_container_width=True,
                key=one_key,
                disabled=one_disabled,
            ):
                _run_upgrade(overall_level, target_level=str(one_step), button_key=one_key)
        with col2:
            two_disabled, two_label = _upgrade_button_state(two_key, two_idle)
            if st.button(
                two_label,
                type="primary",
                use_container_width=True,
                key=two_key,
                disabled=two_disabled,
            ):
                _run_upgrade(overall_level, target_level=str(two_step), button_key=two_key)
    else:
        only_key = "script_coaching_upgrade_one_step_only"
        only_idle = f"한 단계 업그레이드 ({one_step})"
        only_disabled, only_label = _upgrade_button_state(only_key, only_idle)
        if st.button(
            only_label,
            type="primary",
            use_container_width=True,
            key=only_key,
            disabled=only_disabled,
        ):
            _run_upgrade(overall_level, target_level=str(one_step), button_key=only_key)


def _render_diagnose_result(report: Dict[str, Any]) -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭 · 진단 결과")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    level = html.escape(str(report.get("overall_level") or "—"))
    wc = int(report.get("word_count") or 0)
    st.markdown(
        f"""
        <section class="mx-mode-intro" role="region" aria-label="스크립트 진단 리포트">
          <h2 class="mx-mode-title">스크립트 진단 리포트</h2>
          <p class="mx-mode-subtitle">입력한 답변 스크립트를 바탕으로 AI가 정리했어요.</p>
          <p class="tp-mini-topic">예상 등급 · {level} · 단어 수 {wc}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    question = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    script_text = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    if question or script_text:
        parts: List[str] = []
        if question:
            parts.append(f'<p class="sc-q">Q. {html.escape(question)}</p>')
        if script_text:
            parts.append(f'<p class="sc-script">{html.escape(script_text)}</p>')
        _sc_card("내가 작성한 스크립트", "".join(parts))

    summary = str(report.get("summary") or "").strip()
    _sc_card(
        "전체 총평",
        f"<p>{html.escape(summary)}</p>"
        if summary
        else "<p>진단 결과를 아래에서 함께 확인해 주세요.</p>",
    )

    breakdown = report.get("score_breakdown")
    score_html = render_score_donut_bars_html(
        breakdown if isinstance(breakdown, dict) else {},
        _SCORE_LABELS,
        str(report.get("overall_level") or ""),
    )
    if score_html:
        st.markdown("##### 점수 요약")
        st.markdown(score_html, unsafe_allow_html=True)

    strengths = report.get("strengths") or []
    _sc_card(
        "가장 좋았던 점",
        _sc_bullets_html(strengths)
        or "<p>이번 답변에서 강점을 더 끌어올릴 여지가 있어요.</p>",
    )

    st.markdown("##### 바로 고치면 좋은 문법")
    render_grammar_corrections(
        "",
        hits=report.get("grammar_corrections") or [],
        show_heading=False,
        empty_message="이번 스크립트에서 눈에 띄는 문법 슬립은 많지 않았어요.",
    )

    st.markdown("##### 표현 업그레이드")
    render_alternative_expressions(
        "",
        hits=report.get("expression_upgrades") or [],
        show_heading=False,
        empty_message="표현을 한 단계 올릴 만한 포인트를 찾지 못했어요.",
    )

    structure_fb = report.get("structure_feedback")
    if isinstance(structure_fb, dict) and (
        structure_fb.get("good") or structure_fb.get("missing") or structure_fb.get("next")
    ):
        lines: List[str] = []
        for g in structure_fb.get("good") or []:
            lines.append(f"<li>잘한 점: {html.escape(str(g))}</li>")
        for m in structure_fb.get("missing") or []:
            lines.append(f"<li>보완: {html.escape(str(m))}</li>")
        nxt = str(structure_fb.get("next") or "").strip()
        if nxt:
            lines.append(f"<li>다음: {html.escape(nxt)}</li>")
        structure_body = f"<ul>{''.join(lines)}</ul>"
    else:
        structure_body = "<p>도입 → 뒷받침 2~3개 → 마무리 흐름을 의식해 보세요.</p>"
    _sc_card("답변 구조 피드백", structure_body)

    improved = report.get("improved_sentences") or []
    if improved:
        sents: List[str] = []
        for item in improved:
            if isinstance(item, dict):
                sent = str(item.get("sentence") or "").strip()
            else:
                sent = str(item or "").strip()
            if sent:
                sents.append(sent)
        body = _sc_bullets_html(sents)
        if body:
            _sc_card("다시 말하기 추천 문장", body)

    missions = report.get("missions") or []
    if missions:
        body = _sc_bullets_html(missions)
        if body:
            _sc_card("다음 연습 미션", body)

    weaknesses = report.get("weaknesses") or []
    if weaknesses:
        body = _sc_bullets_html(weaknesses)
        if body:
            _sc_card("보완점", body)

    _render_upgrade_section(report)

    if st.button(
        "답변 고쳐서 다시 진단",
        use_container_width=True,
        key="script_coaching_rediagnose_keep_inputs",
    ):
        st.session_state.pop(_KEY_DIAGNOSE_RESULT, None)
        st.session_state[_KEY_STEP] = "input"
        _reset_diagnose_guard()
        _reset_upgrade_guard()
        st.rerun()

    if st.button(
        "새 스크립트 진단하기",
        use_container_width=True,
        key="script_coaching_new_script_diagnose",
    ):
        st.session_state[_KEY_CLEAR_INPUTS] = True
        st.session_state.pop(_KEY_DIAGNOSE_RESULT, None)
        st.session_state[_KEY_STEP] = "input"
        st.rerun()

    if st.button(
        "학습 방식 다시 선택",
        use_container_width=True,
        key="script_coaching_back_portal",
    ):
        from views.mock_exam import reset_to_learning_portal

        clear_script_coaching_session()
        reset_to_learning_portal()
        st.rerun()


def _level_transition_label(report: Dict[str, Any]) -> str:
    mode = str(report.get("mode") or "").strip().lower()
    current = html.escape(str(report.get("current_level") or "—"))
    if mode == "polish":
        return f"{current} → AL 보완"
    target = html.escape(str(report.get("target_level") or "—"))
    return f"{current} → {target}"


def _render_upgrade_result(report: Dict[str, Any]) -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭 · 변환 결과")
    st.markdown(
        '<div class="mx-marker sc-upgrade-ba-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    transition = _level_transition_label(report)
    st.markdown(
        f"""
        <section class="mx-mode-intro" role="region" aria-label="스크립트 변환 리포트">
          <h2 class="mx-mode-title">스크립트 변환 리포트</h2>
          <p class="mx-mode-subtitle">목표 등급 수준으로 다시 쓴 스크립트예요.</p>
          <p class="tp-mini-topic">등급 변환 · {transition}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    original = _resolve_original_script(report)
    upgraded = str(report.get("upgraded_script") or "").strip()

    if original:
        st.markdown(
            '<div class="sc-ba-block">'
            '<div class="sc-ba-label">내 원래 스크립트</div>'
            f'<div class="sc-ba-original"><p>{html.escape(original)}</p></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    if upgraded:
        st.markdown(
            '<div class="sc-ba-block">'
            '<div class="sc-ba-label sc-ba-label--accent">업그레이드</div>'
            f'<div class="sc-ba-upgraded"><p>{html.escape(upgraded)}</p></div>'
            "</div>",
            unsafe_allow_html=True,
        )
    elif not original:
        _sc_card("업그레이드된 스크립트", "<p>변환된 스크립트를 불러오지 못했어요.</p>")

    change_notes = report.get("change_notes") or []
    if change_notes:
        body = _sc_bullets_html(change_notes)
        if body:
            _sc_card("이렇게 바꿨어요", body)

    fill_guides = report.get("fill_in_guides") or []
    if fill_guides:
        body = _sc_bullets_html(fill_guides)
        if body:
            note = (
                "<p>아래 항목은 AI가 지어내지 않고 <strong>직접 추가하면 좋을 내용</strong>이에요. "
                "빈칸을 채워 넣으면 스크립트가 더 풍부해집니다.</p>"
            )
            _sc_card("직접 추가해 보세요", note + body)

    if st.button(
        "진단 결과로 돌아가기",
        use_container_width=True,
        key="script_coaching_back_to_diagnose",
    ):
        st.session_state[_KEY_STEP] = "result"
        st.rerun()

    if st.button(
        "학습 방식 다시 선택",
        use_container_width=True,
        key="script_coaching_back_portal_from_upgrade",
    ):
        from views.mock_exam import reset_to_learning_portal

        clear_script_coaching_session()
        reset_to_learning_portal()
        st.rerun()


def render_script_coaching() -> None:
    """Entry: diagnose form → result report → upgrade result."""
    _ensure_defaults()
    step = str(st.session_state.get(_KEY_STEP) or "input").strip()

    if step == "upgrade_result":
        upgrade_report = st.session_state.get(_KEY_UPGRADE_RESULT)
        if isinstance(upgrade_report, dict) and upgrade_report.get("ok"):
            _render_upgrade_result(upgrade_report)
            return
        st.session_state[_KEY_STEP] = "result"

    if step == "result":
        report = st.session_state.get(_KEY_DIAGNOSE_RESULT)
        if isinstance(report, dict) and report.get("ok"):
            _render_diagnose_result(report)
            return
        else:
            st.session_state[_KEY_STEP] = "input"

    _render_input_form()
    report = st.session_state.get(_KEY_DIAGNOSE_RESULT)
    if isinstance(report, dict) and not report.get("ok"):
        msg = str(report.get("error_message") or "").strip()
        if msg:
            st.error(msg)
