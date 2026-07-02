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

LEVEL_RULE_VERSION = "shared_level_rules_2026_06_ih_al_recalibration"

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
        "LOW words_normalized_90s may cap the level downward — never raise on quantity alone. "
        "When duration/wpm are available: high WPM (e.g. 110+) WITH organized paragraph "
        "discourse, varied connectors, and clear development is supporting evidence for "
        "IH/AL — combine with delivery_quality_guidance; WPM alone never raises the level."
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
            "Organized paragraph discourse: clear opening, connected supporting details, "
            "logical order, natural closing; varied connectors (because, so, however, for example); "
            "vocabulary beyond only like/good/many/very. Some fillers (um, uh) and occasional "
            "backtracking or light STT repetition (e.g. 'has has uh has') are acceptable at IH — "
            "do NOT downgrade to IM2/IM3 for minor fillers when paragraph structure and relevance "
            "are strong. Typical reference (soft, not hard gate): ~100–120 words in mini-mock "
            "3Q combined scope, or a single strong paragraph answer in topic practice."
        ),
    },
    "AL": {
        "connected_speech": "strong paragraph, flexible and detailed",
        "total_words_anchor": {"min": 150, "typical": 160},
        "sentence_count_anchor": {"min": 18, "typical": 20},
        "anchor_scope": "mini_mock_q1_q3_combined",
        "summary": (
            "Assign AL when the criteria below are met; do not withhold AL for an answer that "
            "meets them. AL delivery profile (observe in transcript + payload wpm/duration): "
            "(a) fast, natural delivery — high WPM (e.g. 110+) supports AL when combined with "
            "organized discourse (never WPM alone); "
            "(b) sentence variety — not monotonous; complex sentences linked with varied connectors; "
            "(c) minimal backtracking and filler loops — speech flows without heavy self-correction "
            "chains (light um/uh is fine; stutter loops are not); "
            "(d) attempts advanced/native-like vocabulary naturally; "
            "(e) controlled narration across past AND present time frames when the task requires it. "
            "Typical reference (soft, not hard gate): 150+ words in mini-mock 3Q combined scope."
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
        "ONLY. Observe fillers (um, uh), light backtracking, and STT stutter "
        "repeats in the transcript; minor fillers support IH, heavy loops cap "
        "below IH. Never evaluate pronunciation, intonation, stress, or linking."
    ),
}

SHARED_SCORE_AXIS_PHILOSOPHY: Tuple[str, ...] = (
    "All six axes are scored 0–100 as integers.",
    "Accuracy axes (grammar, vocabulary) do NOT raise the level on their own: "
    "strong grammar with weak structure/relevance cannot reach IH — see STRUCTURE_GATE.",
    "Relevance is a GATING axis, not just one of six. If an answer does not "
    "actually answer the question (question echo / parroting or total off-topic), "
    "it is a non-answer: score relevance very low, do NOT count its words toward "
    "response_amount, and it cannot support IM1 or above on its own — see relevance_gate.",
    "Text-first only: naturalness is transcript-based; pronunciation is never scored. "
    "Delivery/comprehensibility (accent, intelligibility) is intentionally OUT OF "
    "SCOPE here — a live OPIc rater also hears delivery, so a transcript-only grade "
    "may read slightly generous for pronunciation-limited speakers.",
    "Level is decided by FUNCTION and text type FIRST, with word/sentence counts as "
    "corroboration only (see anchor_usage). Tense / time-frame control is not merely "
    "the grammar axis: narrating across past and present is a FUNCTION that gates "
    "Advanced (AL) — see advanced_function_gate.",
    "Transcript-only: use payload wpm / duration_seconds / words_normalized_90s when "
    "present. High WPM plus organized paragraph discourse supports IH/AL; never "
    "promote on WPM alone. Read fillers and backtracking from the transcript text.",
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
        "Prefer a specific past event (what happened, sequence, feeling) when the "
        "student has one — but an HONEST lack-of-experience answer is also valid: "
        "saying they have no direct experience, briefly why, or who handles it at "
        "home (spouse/family) while staying on the question topic. Score such "
        "deflection by fluency and connected sentences, NOT as off-topic or "
        "insufficient. Do NOT cap at IL only because no past narrative was given "
        "(see honest_deflection_guidance). Do NOT apply roleplay rules here."
    ),
    "roleplay": (
        "Speak DIRECTLY to the imagined person (second person 'you'). Complete "
        "exactly what the prompt requires — e.g. 2–3 natural questions if it "
        "asks for questions; a problem + solution/alternative if it asks to "
        "solve a problem; a related past experience if it asks for one. Must "
        "sound conversational. Do NOT judge a roleplay answer as an experience "
        "narrative, and do NOT assume a schedule-change scenario unless the "
        "question_text says so. NOTE: when the prompt asks the student to solve "
        "a problem or react to an unexpected change, this is the ACTFL Advanced "
        "'situation with a complication' task — handling it smoothly (explain the "
        "issue, propose a solution/alternative, manage the interaction) is strong "
        "positive evidence for IH/AL; failing or avoiding it caps at Intermediate."
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
    "0. RELEVANCE / NON-ANSWER GATE FIRST: confirm each answer actually answers its "
    "question. Discard question echoes and fully off-topic non-answers BEFORE counting "
    "anything — their length must never be rewarded (see relevance_gate).",
    "1. CLASSIFY BY FUNCTION / TEXT TYPE FIRST — this is the PRIMARY level driver "
    "(ACTFL is functional, not a word count). For the genuine answers, ask what the "
    "speaker actually DOES: isolated words / lists (NH–IL); creates with language at "
    "the sentence level (IM1–IM2); connected, paragraph-like development (IM3); an "
    "organized paragraph that ATTEMPTS advanced narration/comparison/opinion (IH); or "
    "SUSTAINED, multi-time-frame paragraph discourse (AL). Use the level anchors' "
    "connected_speech field and advanced_function_gate for this.",
    "2. Use response amount only as CORROBORATION, not the driver (see anchor_usage): "
    "total_word_count, total_sentence_count, words_normalized_90s, total_duration_seconds "
    "if available, checked against the anchors. NEVER promote to IH/AL on counts alone.",
    "3. Check quality: relevance, structure, grammar, vocabulary, naturalness, roleplay.",
    "4. ADVANCED FUNCTION GATE for IH vs AL — apply advanced_function_gate. "
    "Complication (roleplay problem-solving) is required ONLY when the item or "
    "exam set includes a roleplay question; single non-roleplay answers (topic practice "
    "description/comparison/experience) reach AL via tense control + sustained paragraph "
    "discourse + delivery_quality_guidance without a roleplay complication.",
    "5. Do not assign IM3/IH if Q3 roleplay fails badly in a mini/mock set that "
    "includes roleplay (see ROLEPLAY_GATE).",
    "6. Do not assign IH/AL if structure or relevance is weak (see STRUCTURE_GATE).",
    "7. IL–IM2: prioritize complete sentence production over advanced vocabulary — "
    "but only for answers that genuinely address the question.",
    "8. IM3–IH: require connector use, longer sentence patterns, paragraph-like development.",
    "9. AL: sustained detail, organization, flexibility, delivery quality, and "
    "multi-time-frame narration when the task requires it — see levels.AL summary "
    "and delivery_quality_guidance.",
    "10. ANTI-DEFLATION: see level_anti_deflation_guidance — do not cap a clear "
    "paragraph answer with minor fillers at IM2/IM3.",
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

RELEVANCE_GATE: str = (
    "RELEVANCE / NON-ANSWER GATE (downward floor — the missing counterpart to the "
    "structure/roleplay caps): a response only counts toward the level if it "
    "ACTUALLY answers its question. The following are NON-ANSWERS and must NOT "
    "raise the level no matter how many words or how perfect the grammar is: "
    "(a) reading or repeating the question prompt back, in whole or in part "
    "(question echo / parroting); (b) speech that never addresses the question "
    "and is entirely off-topic; (c) memorized or random text unrelated to the "
    "prompt. Words from a non-answer do NOT count toward response_amount or the "
    "word/sentence anchors — strip them out BEFORE judging quantity. Treat such "
    "an answer as insufficient_response. Per-answer signals may include "
    "question_echo (true/false), question_overlap_ratio (share of answer words "
    "also in question_text), and novel_word_count (answer words not in the "
    "question): a high overlap with almost no novel content means a question "
    "echo. If most or all answers are non-answers, set overall_level to "
    "'응답 부족' — and even a single such transcript can never reach IM1 or above "
    "on quantity alone (cap at IL at most). IMPORTANT consistency with the loose "
    "relevance philosophy: genuine on-topic answers that branch into extra "
    "detail (TMI) or reuse a few question keywords are NOT penalized — this gate "
    "fires ONLY on true non-answers (question echo or total off-topic). "
    "NOT non-answers: honestly stating no personal experience while staying on "
    "topic (e.g. 'I don't recycle — my wife does it at home') or naturally "
    "redirecting to someone nearby who handles the topic — see honest_deflection_guidance."
)

HONEST_DEFLECTION_GUIDANCE: str = (
    "HONEST NO-EXPERIENCE / NATURAL DEFLECTION (valid OPIc answers): Real OPIc "
    "speakers often say they lack direct experience and explain why, or redirect "
    "to a household member who handles the topic. Example: 'I don't really have "
    "any experience related to recycling because I don't recycle — my wife does "
    "it since she's mostly at home, so you should ask her or my mom.' This IS "
    "answering the question (acknowledges the ask, gives reason/context). Do NOT "
    "treat as off-topic, evasion, or insufficient_response. Score relevance HIGH. "
    "Count all words toward response_amount. Level by FUNCTION: multi-sentence "
    "connected deflection with reasons (because/since/so) can reach IM1–IM2; "
    "paragraph-like flow with connectors can reach IM3. Do NOT assign IL solely "
    "because no past-event narrative was provided. IH+ still requires sustained "
    "past+present paragraph discourse per advanced_function_gate — honest "
    "deflection alone does not earn IH, but it should not be downgraded to IL "
    "when the speaker produces fluent IM1–IM2-level connected speech."
)

ADVANCED_FUNCTION_GATE: str = (
    "ADVANCED FUNCTION GATE (ACTFL Intermediate→Advanced — decides IH vs AL, not word count). "
    "Apply in two modes depending on scope: "
    "MODE A — SINGLE NON-ROLEPLAY ANSWER (topic practice one question; description / routine / "
    "experience / comparison / news_issue without a roleplay prompt): "
    "AL when the speaker SUSTAINS organized paragraph discourse AND shows controlled tense "
    "across the time frames the question needs (e.g. comparison → past+present; description "
    "may be present-focused) AND meets delivery_quality_guidance (varied sentences, connectors, "
    "limited backtracking loops). Do NOT require a roleplay complication in this mode. "
    "MODE B — EXAM OR ITEM INCLUDES ROLEPLAY: all universal checks below PLUS complication "
    "on the roleplay item — weak roleplay caps the SET per ROLEPLAY_GATE, not every item. "
    "UNIVERSAL IH vs AL checks (both modes): "
    "(1) TIME FRAMES — narrate/describe across the major time frames the TASK requires with "
    "controlled tense; present-only when past is required, or past narration that collapses, "
    "caps below AL. "
    "(2) SUSTAIN vs ATTEMPT — IH = ATTEMPTS paragraph-level advanced tasks but cannot fully "
    "SUSTAIN (breaks into lists/short sentences). AL = SUSTAINS paragraph discourse consistently. "
    "(3) COMPLICATION — ONLY in MODE B (roleplay / problem-solving prompts): handling the "
    "unexpected situation smoothly is Advanced evidence; avoiding or failing it on that item "
    "caps that item and may cap the overall exam per ROLEPLAY_GATE — do NOT apply (3) to "
    "non-roleplay description/comparison items. "
    "Summary: AL = sustained paragraph + delivery quality + required time frames for the task; "
    "complication is roleplay-scoped, not a universal third leg for every answer."
)

DELIVERY_QUALITY_GUIDANCE: str = (
    "DELIVERY QUALITY (transcript + payload metrics — IH/AL discriminator): "
    "Use wpm, duration_seconds, and words_normalized_90s from the payload when present. "
    "High WPM (e.g. 110+) WITH organized paragraph structure, varied connectors, and clear "
    "development supports IH or AL — never promote on WPM alone. "
    "From the transcript, observe: filler density (um, uh), backtracking/self-repair loops, "
    "and STT stutter repeats (e.g. 'has has uh has'). Light fillers and occasional repairs "
    "are compatible with IH; heavy loops or list-like monotone caps below IH. "
    "AL profile: faster natural flow, sentence variety, varied connectors, limited backtracking, "
    "advanced vocabulary attempts, and sustained paragraph form."
)

LEVEL_ANTI_DEFLATION_GUIDANCE: str = (
    "LEVEL ANTI-DEFLATION: A well-organized paragraph answer with natural connector use and "
    "minor fillers (um, uh) is IH — do not deflate it to IM2/IM3. Reserve IM2/IM3 for "
    "sentence-level breakdowns, heavy repetition, list-like non-paragraph discourse, or "
    "answers that do not sustain development. Assign AL when AL criteria are met; do not "
    "withhold AL solely because the sample is short or from a mini mock."
)

ANCHOR_USAGE_NOTE: str = (
    "ANCHOR USAGE: total_words_anchor and sentence_count_anchor are TYPICAL REFERENCE "
    "RANGES ONLY — never hard pass/fail gates. Decide level from FUNCTION, text type, and "
    "delivery quality first (decision_guidance, advanced_function_gate, "
    "delivery_quality_guidance). Use word/sentence counts only as corroboration. "
    "If function and quality clearly match IH or AL but counts are modestly below the "
    "anchor (e.g. a single strong 90-second paragraph), do NOT downgrade solely for "
    "count shortfall. A long answer without the level's function does not earn that level. "
    "Never promote to IH/AL on hitting a word anchor alone."
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
        "AL: Flexible, precise, or native-like expressions in natural spoken English — "
        "not forced academic vocabulary; fast organized delivery per delivery_quality_guidance."
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
SHARED_RELEVANCE_GATE = RELEVANCE_GATE
SHARED_HONEST_DEFLECTION_GUIDANCE = HONEST_DEFLECTION_GUIDANCE
SHARED_ADVANCED_FUNCTION_GATE = ADVANCED_FUNCTION_GATE
SHARED_DELIVERY_QUALITY_GUIDANCE = DELIVERY_QUALITY_GUIDANCE
SHARED_LEVEL_ANTI_DEFLATION_GUIDANCE = LEVEL_ANTI_DEFLATION_GUIDANCE
SHARED_ANCHOR_USAGE_NOTE = ANCHOR_USAGE_NOTE
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
        "anchor_usage": ANCHOR_USAGE_NOTE,
        "roleplay_gate": MINI_MOCK_V2_ROLEPLAY_GATE,
        "structure_gate": STRUCTURE_GATE,
        "relevance_gate": RELEVANCE_GATE,
        "honest_deflection_guidance": HONEST_DEFLECTION_GUIDANCE,
        "advanced_function_gate": ADVANCED_FUNCTION_GATE,
        "delivery_quality_guidance": DELIVERY_QUALITY_GUIDANCE,
        "level_anti_deflation_guidance": LEVEL_ANTI_DEFLATION_GUIDANCE,
        "mock_v2_usable_answer_gate": MOCK_V2_USABLE_ANSWER_GATE,
        "vocabulary_rules": MINI_MOCK_V2_VOCABULARY_RULES,
        "connector_rules": MINI_MOCK_V2_CONNECTOR_RULES,
    }
    return json.dumps(block, ensure_ascii=False, indent=2)
