"""
Gemini multimodal pipeline:
  [1] Semantic evaluation (primary scores + verbatim transcription)
  [2] Audio duration metrics (pydub / wave / fallback)
  [3] Rule layer + calibration (eval_grading / eval_rules)

외부 인터페이스 유지:
  analyze_audio_with_ai(), analyze_answer(), evaluate_grading_logic()
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from services.evaluation import ai_diag

from google import genai
from google.genai import types as genai_types

from .audio_mime import resolve_audio_mime
from utils import audio_pipeline_diag
from .eval_audio import build_audio_info
from .eval_config import MODEL_NAME
from .eval_grading import evaluate_grading_logic as run_hybrid_grading, strip_json_fence
from utils.language_detection import detect_language_mismatch, language_mismatch_body
from utils.text_utils import is_real_speech_transcript


logger = logging.getLogger(__name__)

_AVAILABLE_MODELS_CACHE: Dict[str, List[str]] = {}

SEMANTIC_KEYS = (
    "fluency_score",
    "grammar_score",
    "lexical_score",
    "logic_score",
    "semantic_density",
    "discourse_continuity",
    "narrative_depth",
    "elaboration_quality",
    "spontaneity_score",
    "naturalness",
    "tense_stability",
    "pause_stability",
    "repetition_ratio",
    "abandoned_sentence_ratio",
    "pronunciation_clarity",
    "intonation_control",
    "stress_rhythm",
    "linking_naturalness",
)


def _build_semantic_evaluation_prompt(question_text: str, difficulty: int) -> str:
    tgt = "Level 6 (AL target)" if int(difficulty) >= 6 else "Level 5 (IH target)"
    strict = (
        "Be strict on abstract reasoning, repair strategies, and nuanced stance-taking for AL signals.\n"
        if int(difficulty) >= 6
        else "Reward sustained narration and logical progression over memorized idioms.\n"
    )
    return f"""
You are an expert OPIc-style oral examiner. Listen to the attached audio response.

Task:
1) Produce a faithful FULL verbatim transcription (English). Do not summarize.
2) Score the performance using REALISTIC classroom speaking criteria — NOT typing speed or word-count gaming.

ABSOLUTE TRANSCRIPTION RULES — TRUST IS LOST IF YOU VIOLATE THESE:
- Transcribe ONLY what is actually audible in the attached audio.
- If the audio is silent, contains only background noise, or has no
  intelligible speech, set ``transcription`` to an EMPTY STRING (``""``)
  and set ``no_speech_detected`` to ``true``. ALL scores become 0.
- DO NOT fabricate, paraphrase, or "fill in" a likely response.
- DO NOT echo, rephrase, or otherwise reuse any part of the question
  prompt as the user's transcription.
- DO NOT introduce yourself, greet the user, or speak as the user.
- DO NOT output commentary, markdown, or any text outside the JSON object.

Grading philosophy:
- Natural narration, elaboration, discourse continuity, spontaneity, and grammar matter MORE than raw speed.
- Penalize filler dependence, shallow repetition, template memorization, broken clauses, and tense instability.
- Idioms are optional SMALL flair — never sufficient alone for top tiers.
- Pronunciation, intonation, stress, rhythm, and linking are a LIGHT supporting axis (~12% of quality).
  Score clarity, rhythm, stress placement, and intelligibility from the audio — NOT native-like accent.

Accent fairness (required):
- Do not penalize the speaker merely for having a Korean accent.
- Penalize only when pronunciation, stress, rhythm, or intonation reduces intelligibility
  or makes the answer difficult to follow.
- A Korean accent is acceptable if words are understandable and rhythm supports meaning.

Question prompt for context (DO NOT echo this text into transcription):
""" + repr(question_text or "") + f"""

Calibration hint for expectation band: {tgt}
{strict}

Return ONLY one JSON object (no markdown fences). Required schema — integers 0–100 inclusive unless noted:
{{
  "transcription": "<full verbatim transcript, or '' if no speech detected>",
  "no_speech_detected": false,
  "estimated_level": "<NH|IL|IM1|IM2|IM3|IH|AL>",

  "fluency_score": 0,
  "grammar_score": 0,
  "lexical_score": 0,
  "logic_score": 0,

  "semantic_density": 0,
  "discourse_continuity": 0,
  "narrative_depth": 0,
  "elaboration_quality": 0,
  "spontaneity_score": 0,
  "naturalness": 0,

  "tense_stability": 0,
  "pause_stability": 0,

  "repetition_ratio": 0,
  "abandoned_sentence_ratio": 0,

  "pronunciation_clarity": 0,
  "intonation_control": 0,
  "stress_rhythm": 0,
  "linking_naturalness": 0,

  "feedback": "<concise Korean coaching paragraph, or empty if no speech>"
}}

Pronunciation dimension guide (0–100, higher = better):
- pronunciation_clarity: how clearly words are pronounced and understood
- intonation_control: natural rise/fall; avoid flat robotic delivery
- stress_rhythm: stress on content words; natural English rhythm
- linking_naturalness: connected speech sounds natural, not overly word-by-word

Interpret ratios as severity scales (higher = worse) for repetition/abandonment.
""".strip()


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = strip_json_fence(text or "")
    try:
        maybe = json.loads(cleaned)
        if isinstance(maybe, dict):
            return maybe
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            maybe = json.loads(cleaned[start : end + 1])
            if isinstance(maybe, dict):
                return maybe
        except Exception:
            pass
    candidates = re.findall(r"\{[\s\S]*?\}", cleaned)
    for cand in reversed(candidates):
        try:
            maybe = json.loads(cand)
            if isinstance(maybe, dict):
                return maybe
        except Exception:
            continue
    return None


def _try_extract_transcription_from_broken_json(raw_text: str) -> str:
    """Best-effort transcription field recovery when JSON parsing fails."""
    text = raw_text or ""
    for key in ("transcription", "transcript"):
        pattern = rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        fragment = match.group(1)
        try:
            return str(json.loads(f'"{fragment}"')).strip()
        except Exception:
            return (
                fragment.replace("\\n", "\n")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
                .strip()
            )
    return ""


def _slice_semantic(parsed: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in SEMANTIC_KEYS:
        if k in parsed and parsed[k] is not None:
            out[k] = parsed[k]
    return out


def _safe_debug_print(message: str) -> None:
    try:
        print(message, flush=True)
    except BrokenPipeError:
        logger.warning("stdout pipe closed")
    except Exception:
        logger.exception("debug print failed")


def _list_available_models(api_key: str) -> List[str]:
    """List Gemini model ids (extra API call). Not used on mock-exam analysis hot path.

    Kept for optional debugging when ``GEMINI_DEBUG_LIST_MODELS=1`` or for
    ad-hoc tooling; ``analyze_audio_with_ai`` uses a fixed candidate list only.
    """
    cache_hit = _AVAILABLE_MODELS_CACHE.get(api_key)
    if cache_hit is not None:
        return cache_hit
    try:
        client = genai.Client(api_key=api_key)
        models: List[str] = []
        for m in client.models.list():
            name = getattr(m, "name", "") or ""
            if name:
                models.append(name)
                _safe_debug_print(f"Available Model: {name}")
        _AVAILABLE_MODELS_CACHE[api_key] = models
        return models
    except Exception as e:
        _safe_debug_print(f"[list_models failed] {type(e).__name__}: {e}")
        _AVAILABLE_MODELS_CACHE[api_key] = []
        return []


def _normalize_model_name(model_name: str) -> str:
    name = (model_name or "").strip()
    if not name:
        return ""
    for prefix in ("models/", "publishers/google/models/"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _build_model_candidates() -> List[str]:
    """Fixed Flash stack for mock exam — no ``models.list`` on the hot path.

    Order: configured ``MODEL_NAME`` (default ``gemini-2.5-flash``, overridable
    via ``GEMINI_MODEL``), then stable fallbacks. Duplicates removed.
    """
    out: List[str] = []
    for raw in (
        MODEL_NAME,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ):
        n = _normalize_model_name(raw)
        if n and n not in out:
            out.append(n)
    return out


def evaluate_grading_logic(
    audio_info: Dict[str, Any],
    transcript: str,
    question_text: str = "",
    *,
    semantic: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rule + calibration layer (Gemini scores optional). 외부 호환 시 semantic 생략 가능."""
    return run_hybrid_grading(audio_info, transcript, question_text, semantic=semantic)


def analyze_audio_with_ai(
    audio_bytes: bytes,
    question_text: str,
    api_key: str,
    difficulty: int = 5,
    *,
    mime_guess: Optional[str] = None,
):
    if not audio_bytes:
        ai_diag.log_pipeline_end(outcome="no_audio_bytes")
        return {"error": "녹음 바이트가 비어 있습니다.", "diagnosis_status": "api_error"}

    ai_diag.update_diag_context(audio_bytes_len=len(audio_bytes))
    ai_diag.log_pipeline_start()

    try:
        model_candidates = _build_model_candidates()
        logger.info("Gemini semantic fixed candidate queue: %s", model_candidates)

        mime_type = resolve_audio_mime(audio_bytes, mime_guess)
        audio_info = build_audio_info(audio_bytes, mime_type)
        audio_info["mime_guess"] = mime_type

        client = genai.Client(api_key=api_key)
        prompt = _build_semantic_evaluation_prompt(question_text, int(difficulty))

        parts = [
            genai_types.Part.from_text(text=prompt),
            genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        ]
        contents = [genai_types.Content(role="user", parts=parts)]
        config = genai_types.GenerateContentConfig(
            temperature=0.25,
            max_output_tokens=4096,
        )

        response = None
        model_used = None
        tried_models: List[str] = []
        last_model_exc: Optional[BaseException] = None

        for fallback_index, candidate in enumerate(model_candidates):
            ai_diag.update_diag_context(fallback_index=fallback_index)
            ai_diag.log_semantic_start(model_id=candidate)
            logger.info("Gemini semantic attempt model_id=%s", candidate)
            tried_models.append(candidate)
            t0 = time.perf_counter()
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=contents,
                    config=config,
                )
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                model_used = candidate
                ai_diag.log_semantic_success(model_id=candidate, elapsed_ms=elapsed_ms)
                logger.info("Gemini semantic success model_id=%s", candidate)
                break
            except Exception as model_exc:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                last_model_exc = model_exc
                err_text = str(model_exc)
                err_cls = type(model_exc).__name__
                ai_diag.log_semantic_failure(
                    model_id=candidate,
                    elapsed_ms=elapsed_ms,
                    error_type=err_cls,
                    error_message=err_text,
                )
                logger.warning(
                    "Gemini semantic failure model_id=%s exc_type=%s",
                    candidate,
                    err_cls,
                )
                if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                    logger.warning("Gemini quota on model_id=%s", candidate)
                    ai_diag.log_pipeline_end(outcome="quota_429")
                    return {
                        "error": "API 할당량이 잠시 초과되었습니다. 잠시 후 다시 시도해 주세요.",
                        "diagnosis_status": "api_error",
                    }
                if "404" in err_text or "NOT_FOUND" in err_text:
                    logger.info(
                        "Gemini model not found (try next): model_id=%s",
                        candidate,
                    )
                    continue
                # 503 / UNAVAILABLE / timeout / overload — try next fixed fallback.
                logger.warning(
                    "Gemini transient failure model_id=%s exc_type=%s (try next candidate)",
                    candidate,
                    err_cls,
                )
                continue

        if response is None:
            logger.error(
                "Gemini semantic exhausted candidates=%s last_exc_type=%s",
                tried_models,
                type(last_model_exc).__name__ if last_model_exc else None,
            )
            ai_diag.log_pipeline_end(outcome="exhausted_candidates")
            return {
                "error": "AI 분석 연결에 일시적인 문제가 있었습니다. 잠시 후 다시 시도해 주세요.",
                "diagnosis_status": "api_error",
                "model_used": tried_models[-1] if tried_models else MODEL_NAME,
            }

        raw_text = (getattr(response, "text", "") or "").strip()
        if not raw_text:
            cand_texts: List[str] = []
            for cand in getattr(response, "candidates", None) or []:
                content = getattr(cand, "content", None)
                for part in getattr(content, "parts", None) or []:
                    t = getattr(part, "text", None)
                    if t:
                        cand_texts.append(t)
            raw_text = "\n".join(cand_texts).strip()

        if not raw_text:
            logger.error("Gemini returned empty text after success model_id=%s", model_used)
            ai_diag.log_pipeline_end(outcome="empty_response_text")
            return {
                "error": "AI 응답이 비어 있었습니다. 잠시 후 다시 시도해 주세요.",
                "diagnosis_status": "api_error",
                "model_used": model_used or MODEL_NAME,
            }

        parsed = _extract_json_object(raw_text)
        parse_fragment = False
        if parsed is None:
            recovered = _try_extract_transcription_from_broken_json(raw_text)
            parse_fragment = True
            parsed = {
                "transcription": recovered,
                "no_speech_detected": not recovered,
                "feedback": "",
                "raw_parse_fragment": True,
            }

        # Trust gate (single source of truth lives in utils.text_utils):
        # reject anything that doesn't look like genuine recognized speech
        # — placeholder phrases, question-echo, JSON fragments, etc.
        raw_transcription = str(
            parsed.get("transcription") or parsed.get("transcript") or ""
        ).strip()
        lang_from_model = str(
            parsed.get("detected_language")
            or parsed.get("response_language")
            or parsed.get("language")
            or ""
        ).strip().lower()
        lang_kind = detect_language_mismatch(raw_transcription)
        if not lang_kind and lang_from_model:
            if any(tok in lang_from_model for tok in ("ko", "korean", "hangul", "한국")):
                lang_kind = "korean"
            elif lang_from_model not in ("en", "english", "eng", ""):
                lang_kind = "possible_non_english"

        if lang_kind:
            preview = raw_transcription[:120]
            semantic_slice = _slice_semantic(parsed)
            grading = run_hybrid_grading(
                audio_info, "", question_text, semantic=semantic_slice
            )
            metrics = grading.get("metrics") or {}
            ai_diag.log_pipeline_end(outcome="non_english")
            return {
                "diagnosis_status": "non_english",
                "analysis_status": "non_english",
                "no_speech_detected": False,
                "trust_gate_passed": False,
                "trust_gate_rejected": False,
                "trust_gate_result": f"language_{lang_kind}",
                "transcript": "",
                "non_english_preview": preview,
                "language_mismatch_kind": lang_kind,
                "estimated_level": "측정 불가",
                "estimated_level_display": "측정 불가",
                "estimated_range": "",
                "summary_speech_rehab": language_mismatch_body(lang_kind),
                "prescription": language_mismatch_body(lang_kind),
                "tense_appropriateness_feedback": "",
                "wpm": metrics.get("wpm", 0),
                "sentence_count": 0,
                "word_count": 0,
                "fact_scores": {"text_type": 0.0, "accuracy": 0.0},
                "rubric_scores": {"fluency": 0, "lexical": 0, "logic": 0, "grammar": 0},
                "model_used": model_used or "unknown",
                "audio_mime_guess": mime_type,
                "source_audio_size_bytes": len(audio_bytes),
                "question_type": grading.get("question_type", "A"),
                "final_grade_score": 0,
                "semantic_feedback": "",
                "semantic_dimensions": grading.get("semantic_dimensions") or {},
                "pronunciation_scores": {},
                "pronunciation_feedback": "",
                "grading_rule_flags": {},
                "raw_text_parse_failed": "",
            }

        ai_no_speech_flag = bool(parsed.get("no_speech_detected"))
        trust_passed = is_real_speech_transcript(raw_transcription)

        if trust_passed:
            transcription = raw_transcription
            no_speech = False
            diagnosis_status = "ok"
            trust_gate_result = "passed"
            trust_gate_rejected = False
        elif raw_transcription:
            transcription = ""
            no_speech = False
            diagnosis_status = "needs_review"
            trust_gate_result = "rejected_nonempty"
            trust_gate_rejected = True
        elif ai_no_speech_flag:
            transcription = ""
            no_speech = True
            diagnosis_status = "no_speech"
            trust_gate_result = "ai_no_speech_flag"
            trust_gate_rejected = False
        else:
            transcription = ""
            no_speech = True
            diagnosis_status = "no_speech"
            trust_gate_result = "empty_transcript"
            trust_gate_rejected = False

        audio_pipeline_diag.log_transcript(transcript=transcription or raw_transcription)
        audio_pipeline_diag.log_after_gemini(
            response_ok=True,
            raw_keys=sorted(parsed.keys()) if isinstance(parsed, dict) else [],
        )

        semantic_slice = _slice_semantic(parsed)
        grading = run_hybrid_grading(audio_info, transcription, question_text, semantic=semantic_slice)

        metrics = grading.get("metrics") or {}
        priority_scores = grading.get("priority_scores") or {}
        sem_flat = grading.get("semantic_dimensions") or {}

        ai_grade_hint = (parsed.get("estimated_level") or "").strip()
        final_level = grading.get("estimated_level") or ai_grade_hint or "측정 불가"
        summary_ai = (parsed.get("feedback") or "").strip()
        summary_rule = (grading.get("summary_line") or "").strip()
        summary_parts = [p for p in (summary_ai, summary_rule) if p]
        summary_speech_rehab = " ".join(summary_parts).strip() or "분석 피드백이 비어 있습니다."
        tense_feedback = (grading.get("tense_appropriateness_feedback") or "").strip()
        prescription = " ".join([summary_speech_rehab, tense_feedback]).strip()

        fact_scores = {
            "text_type": round(
                (sem_flat.get("discourse_continuity", 50) + sem_flat.get("narrative_depth", 50)) / 2.0,
                1,
            ),
            "accuracy": round(sem_flat.get("grammar_score", 50), 1),
        }

        rubric_scores = {
            "fluency": priority_scores.get("fluency", 0),
            "lexical": priority_scores.get("lexical", 0),
            "logic": priority_scores.get("logic", 0),
            "grammar": priority_scores.get("grammar", 0),
        }

        parse_failed = ""
        if parse_fragment or parsed.get("raw_parse_fragment"):
            parse_failed = raw_text[:1200]

        ai_diag.log_pipeline_end(outcome=diagnosis_status)
        return {
            "diagnosis_status": diagnosis_status,
            "no_speech_detected": no_speech,
            "trust_gate_passed": trust_passed,
            "trust_gate_rejected": trust_gate_rejected,
            "trust_gate_result": trust_gate_result,
            "raw_transcript_rejected": raw_transcription if trust_gate_rejected else "",
            "transcript": transcription,
            "estimated_level": final_level,
            "estimated_level_display": grading.get("estimated_level_display") or final_level,
            "estimated_range": grading.get("estimated_range") or "",
            "summary_speech_rehab": summary_speech_rehab,
            "prescription": prescription,
            "tense_appropriateness_feedback": tense_feedback,
            "wpm": metrics.get("wpm", 0),
            "sentence_count": metrics.get("sentence_count", 0),
            "word_count": metrics.get("word_count", 0),
            "fact_scores": fact_scores,
            "rubric_scores": rubric_scores,
            "model_used": model_used or "unknown",
            "audio_mime_guess": mime_type,
            "source_audio_size_bytes": len(audio_bytes),
            "question_type": grading.get("question_type", "A"),
            "final_grade_score": grading.get("final_grade_score", 0),
            "ai_grade_raw": ai_grade_hint,
            "semantic_feedback": summary_ai,
            "semantic_dimensions": sem_flat,
            "pronunciation_scores": grading.get("pronunciation_scores") or {},
            "pronunciation_feedback": (grading.get("pronunciation_feedback") or "").strip(),
            "grading_rule_flags": grading.get("rule_flags") or {},
            "novice_band": grading.get("novice_band"),
            "audio_metrics": {
                "duration_seconds": metrics.get("duration_seconds"),
                "duration_method": audio_info.get("duration_method"),
            },
            "raw_text_parse_failed": parse_failed,
        }
    except Exception as e:
        logger.exception("Gemini multimodal pipeline unexpected failure: %s", e)
        ai_diag.log_pipeline_end(outcome="exception")
        return {
            "error": "AI 분석 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "diagnosis_status": "api_error",
            "model_used": "unknown",
        }


def analyze_answer(
    audio_data: bytes,
    question_text: str,
    api_key: str,
    *,
    mime_guess: Optional[str] = None,
):
    return analyze_audio_with_ai(
        audio_data, question_text, api_key, mime_guess=mime_guess
    )


def list_available_gemini_models(api_key: str) -> List[str]:
    client = genai.Client(api_key=api_key)
    models: List[str] = []
    for m in client.models.list():
        name = getattr(m, "name", "") or ""
        if "gemini" in name.lower():
            models.append(name)
    return models
