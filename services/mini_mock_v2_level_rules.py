"""OPIc-style evaluation calibration — SHARED single source of truth (no API calls).

# This file is the SINGLE SOURCE OF TRUTH for ALL OPIc evaluation calibration:
#   - Mini Mock V2 (3-question diagnosis)
#   - Mock V2 (15-question full exam)
#   - Topic Practice V2 (single-question practice feedback)
#
# All three rubric.py builders MUST read from format_level_rules_for_prompt().
# No rubric file may hardcode level anchors, speech-rate bands, score-axis
# definitions, gates, or question-type guidance.
#
# Speech-rate band numbers live ONLY in services/speech_rate_scoring.py
# (WORDS_IN_90S_BANDS). This file references them, never copies them.
#
# Update calibration here after beta testing. analysis.py must not define
# separate level thresholds.
#
# NOTE: filename keeps the historical "mini_mock_v2" name for import stability.
# It is now shared; SHARED_* aliases are the preferred names in new code.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

LEVEL_RULE_VERSION = "shared_level_rules_2026_05_beta_06"

# ---------------------------------------------------------------------------
# DURATION / WPM CONTEXT
# ---------------------------------------------------------------------------

MINI_MOCK_V2_DURATION_CONTEXT: Dict[str, Any] = {
    "il_to_im2_total_seconds": {
        "min": 60,
        "max": 80,
        "note": "IL–IM2 mini mock often shows ~60–80s total speaking time across Q1–Q3.",
    },
    "ih_to_al_total_seconds": {
        "min": 80,
        "max": 100,
        "note": "IH–AL mini mock often shows ~80–100s total speaking time across Q1–Q3.",
    },
    "unavailable_policy": (
        "If duration is unavailable, do not punish directly. "
        "Use total_word_count and total_sentence_count more heavily."
    ),
    "available_policy": (
        "If duration is available, use it as supporting evidence for "
        "response_amount and naturalness only — not as a sole level driver."
    ),
    "stt_reliability_policy": (
        "STT may drop words or include leading/trailing silence in duration. "
        "Treat speech-rate as a DOWNWARD-ONLY signal: a low words_normalized_90s "
        "may cap the level, but a high value must NOT raise it on its own. "
        "When duration_method indicates an estimate (not measured), lean on "
        "word/sentence counts rather than WPM."
    ),
}

MINI_MOCK_V2_WPM_RULES: Dict[str, str] = {
    "role": "scoring_required",
    "reference_window_seconds": "90",
    "bands_source": (
        "speech_rate_scoring.WORDS_IN_90S_BANDS — see speech_rate_90s block below; "
        "do not restate band numbers anywhere else."
    ),
    "use_fields": (
        "aggregate_metrics.words_normalized_90s, speech_rate_level, "
        "response_amount_score_rule, average_wpm"
    ),
    "response_amount": (
        "score_breakdown.response_amount must align with the 90s word bands; "
        "the app blends a rule score (65%) with your estimate (35%)."
    ),
    "overall_level_cap": (
        "Do not assign a level above speech_rate_level from quantity alone; "
        "quality (roleplay, structure, grammar, relevance) can still lower the level. "
        "A high speech rate never raises the level by itself."
    ),
    "do_not_penalize_unavailable": (
        "If wpm_available is false, use total_word_count only; do not mark insufficient for missing WPM."
    ),
}

# ---------------------------------------------------------------------------
# LEVEL ANCHORS
# ---------------------------------------------------------------------------
MINI_MOCK_V2_LEVEL_RULES: Dict[str, Dict[str, Any]] = {
    "NH": {
        "connected_speech": "isolated words or one memorized sentence",
        "total_words_anchor": {"typical": 6, "max": 10},
        "sentence_count_anchor": {"typical": 0, "max": 1},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Speaks mostly in isolated words; around 6 words total or one memorized sentence; "
            "little or no connected sentence production."
        ),
    },
    "IL": {
        "connected_speech": "simple sentences",
        "total_words_anchor": {"min": 15, "max": 30, "typical": 22},
        "sentence_count_anchor": {"min": 3, "max": 5, "typical": 4},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Simple sentences; around 15–30 total words and ~4 short sentences; "
            "mostly sentence-level production."
        ),
    },
    "IM1": {
        "connected_speech": "sentence units with basic communication",
        "total_words_anchor": {"min": 40, "max": 60, "typical": 50},
        "sentence_count_anchor": {"min": 6, "max": 10, "typical": 8},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Sentence units; around 40–60 total words and ~8 sentences; "
            "basic communication, limited detail."
        ),
    },
    "IM2": {
        "connected_speech": "groups of sentences, still basic structure",
        "total_words_anchor": {"min": 60, "max": 80, "typical": 70},
        "sentence_count_anchor": {"min": 8, "max": 12, "typical": 10},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Groups of sentences; around 60–80 total words and ~10 sentences; "
            "understandable with some detail, but structure still basic."
        ),
    },
    "IM3": {
        "connected_speech": "paragraph-like development begins",
        "total_words_anchor": {"min": 80, "max": 100, "typical": 90},
        "sentence_count_anchor": {"min": 10, "max": 14, "typical": 12},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Paragraph-like development; around 80–100 words and ~12 sentences; "
            "connectors and longer patterns appear; grammar/tense errors still visible."
        ),
    },
    "IH": {
        "connected_speech": "organized paragraph form",
        "total_words_anchor": {"min": 100, "max": 120, "typical": 110},
        "sentence_count_anchor": {"min": 12, "max": 16, "typical": 13},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Paragraph form; around 100–120 words and 12+ sentences; organized, relevant, extended; "
            "connectors used well; solid Q3 roleplay; vocabulary beyond only like/good/many/very."
        ),
    },
    "AL": {
        "connected_speech": "strong paragraph, flexible and detailed",
        "total_words_anchor": {"min": 150, "typical": 160},
        "sentence_count_anchor": {"min": 18, "typical": 20},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Strong paragraph; 150+ words and ~20 sentences; flexible, detailed, organized; "
            "attempts native-like or advanced expressions. Do not assign AL easily in 3-question mini."
        ),
    },
}

SHARED_SCORE_AXES: Dict[str, str] = {
    "response_amount": (
        "Quantity and development for the question type; must align with the "
        "90s word bands. Do not reward long but irrelevant answers."
    ),
    "relevance": (
        "Fit to the actual question_text and question type. Judge each answer "
        "against ITS OWN question — never against a different question type."
    ),
    "structure": (
        "Organization and discourse flow in the transcript: clear opening, "
        "2–3 supporting details, logical order, natural closing or feeling. "
        "Disconnected sentences or list-only answers score low."
    ),
    "grammar": (
        "Tense, subject-verb agreement, sentence completion, word order; "
        "prepositions/articles only when they affect clarity. Clarity over "
        "perfection — do not over-penalize minor errors if meaning is clear."
    ),
    "vocabulary": (
        "Range, specificity, variety; natural spoken English. Penalize overuse "
        "of vague words (good, nice, many, very, thing, place, stuff) and "
        "obvious Korean-style direct translation. Do not force academic words."
    ),
    "naturalness": (
        "Conversational tone, connector variety, repetition control, sentence "
        "flow, and whether the answer sounds memorized/robotic — TRANSCRIPT "
        "ONLY. Never evaluate pronunciation, intonation, stress, or linking."
    ),
}

SHARED_SCORE_AXIS_PHILOSOPHY: Tuple[str, ...] = (
    "All six axes are scored 0–100 as integers.",
    "Accuracy axes (grammar, vocabulary) do NOT raise the level on their own: "
    "strong grammar with weak structure/relevance cannot reach IH — see STRUCTURE_GATE.",
    "Text-first only: naturalness is transcript-based; pronunciation is never scored.",
)

SHARED_QUESTION_TYPE_GUIDANCE: Dict[str, str] = {
    "description": (
        "Describe a place, person, object, or routine clearly with concrete "
        "details (location, features, reasons, feelings). Flag vague-only "
        "answers (good/nice/many/thing) without detail."
    ),
    "routine": (
        "A habitual activity: frequency, sequence, reasons, and one small "
        "example. Present-tense habitual framing."
    ),
    "experience": (
        "A specific past event: what happened, sequence of events, and the "
        "feeling or why it was memorable. Do NOT apply roleplay rules here."
    ),
    "roleplay": (
        "Speak DIRECTLY to the imagined person (second person 'you'). Complete "
        "exactly what the prompt requires — e.g. 2–3 natural questions if it "
        "asks for questions; a problem + solution/alternative if it asks to "
        "solve a problem; a related past experience if it asks for one. Must "
        "sound conversational. Do NOT judge a roleplay answer as an experience "
        "narrative, and do NOT assume a schedule-change scenario unless the "
        "question_text says so."
    ),
    "comparison": (
        "Full-exam advanced item: compare two things clearly WITH reasons; "
        "not a generic single-topic description."
    ),
    "news_issue": (
        "Full-exam advanced item: address the issue with an opinion or "
        "observation; not an off-topic personal narrative."
    ),
}

MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE: Tuple[str, ...] = (
    "1. First check response amount: total_word_count, total_sentence_count, "
    "words_normalized_90s, total_duration_seconds if available, and connected "
    "speech level vs level anchors.",
    "2. Then check quality: relevance, structure, grammar, vocabulary, naturalness, roleplay.",
    "3. Do not assign IH/AL based only on word count.",
    "4. Do not assign IM3/IH if Q3 roleplay fails badly (see ROLEPLAY_GATE).",
    "5. Do not assign IH/AL if structure or relevance is weak (see STRUCTURE_GATE).",
    "6. IL–IM2: prioritize sentence production and answer length over advanced vocabulary.",
    "7. IM3–IH: require connector use, longer sentence patterns, paragraph-like development.",
    "8. AL: requires strong detail, organization, flexibility, more native-like expressions — rare in mini mock.",
)

MINI_MOCK_V2_ROLEPLAY_GATE: str = (
    "ROLEPLAY GATE: If a roleplay prompt asks the student to speak to another "
    "person or ask questions, the answer must directly address that person, "
    "complete the roleplay task, include 2–3 natural questions when required, "
    "and sound conversational. If the roleplay answer is weak or off-task, do "
    "NOT give IH or AL overall — even if other answers are long, cap at IM3 "
    "unless overall performance clearly compensates."
)

STRUCTURE_GATE: str = (
    "STRUCTURE GATE: IH and AL require organized, paragraph-level discourse — "
    "a clear opening, 2–3 connected supporting details, logical order, and a "
    "natural closing. If structure is weak (disconnected sentences, list-only "
    "answers, no development) OR relevance is weak (answer drifts from the "
    "question), do NOT assign IH or AL, even when grammar and vocabulary scores "
    "are high. Strong accuracy with sentence-level-only discourse caps at IM3. "
    "This mirrors real OPIc: text type and task completion — not grammatical "
    "perfection — separate IM from IH."
)

MOCK_V2_USABLE_ANSWER_GATE: Dict[str, Any] = {
    "usable_answer_definition": "An answer with roughly 5 or more words of real English transcript.",
    "insufficient_response_min": 3,
    "ih_min_usable_answers": 10,
    "al_min_usable_answers": 13,
    "rule": (
        "Full 15-question exam only. If fewer than 3 answers are usable, set "
        "overall_level = '응답 부족'. Do not assign IH unless at least 10 answers "
        "are usable; do not assign AL unless at least 13 are usable. This is a "
        "completion gate — answering only part of the exam cannot reach IH/AL "
        "regardless of how strong the answered items are."
    ),
}

MINI_MOCK_V2_VOCABULARY_RULES: Dict[str, str] = {
    "IL_IM2": (
        "IL–IM2: Do not overemphasize advanced vocabulary; complete sentences and basic communication matter more."
    ),
    "IM3_IH": (
        "IM3–IH: Penalize overuse of vague words (like, good, many, very, thing, place, stuff); "
        "reward specific natural alternatives."
    ),
    "AL": (
        "AL: Attempt flexible, precise, or native-like expressions; natural spoken English preferred — "
        "not forced academic vocabulary."
    ),
}

MINI_MOCK_V2_CONNECTOR_RULES: Dict[str, str] = {
    "IM3_IH": (
        "IM3–IH: Should show connectors (because, so, but, also, however, for example, after that, "
        "even though, while) and longer sentence patterns; answer feels like a paragraph."
    ),
    "IL_IM2": (
        "IL–IM2: Connectors helpful but not required; focus on enough complete sentences."
    ),
}

MINI_MOCK_V2_CONNECTOR_MARKERS: Tuple[str, ...] = (
    "because",
    "so ",
    "but ",
    "also",
    "however",
    "for example",
    "after that",
    "even though",
    "while ",
)

MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES: Tuple[str, ...] = (
    "단어 수는 IM2 이상에 가까우나, Q3 롤플레이 과제 수행이 약해서 IH로 보기는 어렵습니다.",
    "문장 수는 충분하지만, 같은 표현이 반복되어 자연스러움 점수가 낮아졌습니다.",
    "문법은 안정적이지만 문장이 단편적으로 나열되어 구조 점수가 낮아 IH로 올리기 어렵습니다.",
    "IL–IM2 단계에서는 고급 어휘보다 완성된 문장을 더 많이 만드는 것이 우선입니다.",
    "IH 이상을 목표로 하려면 Q3에서 상대에게 자연스럽게 질문하고 대안을 제시하는 능력이 필요합니다.",
)

# Backward-compatible aliases
DURATION_CONTEXT = MINI_MOCK_V2_DURATION_CONTEXT
WPM_RULES = MINI_MOCK_V2_WPM_RULES
LEVEL_DECISION_GUIDANCE = MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE
ROLEPLAY_GATE = MINI_MOCK_V2_ROLEPLAY_GATE
VOCABULARY_RULES = MINI_MOCK_V2_VOCABULARY_RULES
CONNECTOR_RULES = MINI_MOCK_V2_CONNECTOR_RULES
FEEDBACK_STYLE_EXAMPLES = MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES

SHARED_LEVEL_RULES = MINI_MOCK_V2_LEVEL_RULES
SHARED_DURATION_CONTEXT = MINI_MOCK_V2_DURATION_CONTEXT
SHARED_WPM_RULES = MINI_MOCK_V2_WPM_RULES
SHARED_LEVEL_DECISION_GUIDANCE = MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE
SHARED_ROLEPLAY_GATE = MINI_MOCK_V2_ROLEPLAY_GATE
SHARED_STRUCTURE_GATE = STRUCTURE_GATE
SHARED_VOCABULARY_RULES = MINI_MOCK_V2_VOCABULARY_RULES
SHARED_CONNECTOR_RULES = MINI_MOCK_V2_CONNECTOR_RULES
SHARED_FEEDBACK_STYLE_EXAMPLES = MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES


def format_score_axes_for_prompt() -> str:
    """Bullet list of six score_breakdown axes for rubric prompts."""
    return "\n".join(f"- {key}: {desc}" for key, desc in SHARED_SCORE_AXES.items())


def format_level_rules_for_prompt() -> str:
    """Serialize ALL shared evaluation calibration for rubric injection."""
    from services.speech_rate_scoring import (
        REFERENCE_SPEECH_SECONDS,
        WORDS_IN_90S_BANDS,
        describe_words_in_90s_bands,
    )

    block = {
        "level_rule_version": LEVEL_RULE_VERSION,
        "levels": MINI_MOCK_V2_LEVEL_RULES,
        "score_axes": SHARED_SCORE_AXES,
        "score_axis_philosophy": list(SHARED_SCORE_AXIS_PHILOSOPHY),
        "question_type_guidance": SHARED_QUESTION_TYPE_GUIDANCE,
        "duration_context": MINI_MOCK_V2_DURATION_CONTEXT,
        "wpm_rules": MINI_MOCK_V2_WPM_RULES,
        "speech_rate_90s": {
            "reference_window_seconds": REFERENCE_SPEECH_SECONDS,
            "bands_human_readable": describe_words_in_90s_bands(),
            "words_in_90s_by_level": {
                k: {"min": v[0], "max": v[1]} for k, v in WORDS_IN_90S_BANDS.items()
            },
        },
        "decision_guidance": list(MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE),
        "roleplay_gate": MINI_MOCK_V2_ROLEPLAY_GATE,
        "structure_gate": STRUCTURE_GATE,
        "mock_v2_usable_answer_gate": MOCK_V2_USABLE_ANSWER_GATE,
        "vocabulary_rules": MINI_MOCK_V2_VOCABULARY_RULES,
        "connector_rules": MINI_MOCK_V2_CONNECTOR_RULES,
    }
    return json.dumps(block, ensure_ascii=False, indent=2)
