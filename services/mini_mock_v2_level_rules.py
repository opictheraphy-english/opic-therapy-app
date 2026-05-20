"""Mini Mock V2 OPIc-style level threshold anchors — calibration config only (no API calls).

# Single source of truth for Mini Mock V2 level calibration.
# Update this file after beta testing.
# rubric.py should read from this file.
# analysis.py should not define separate level thresholds.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

LEVEL_RULE_VERSION = "mini_v2_level_rules_2026_05_beta_05"

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
}

MINI_MOCK_V2_WPM_RULES: Dict[str, str] = {
    "role": "supporting_only",
    "do_not_boost": "Do not raise overall_level based on WPM alone.",
    "do_not_penalize_unavailable": (
        "Do not mark an answer insufficient only because WPM is 0 or wpm_available is false."
    ),
}

# Practical OPIc diagnostic anchors — NOT official ACTFL scores.
MINI_MOCK_V2_LEVEL_RULES: Dict[str, Dict[str, Any]] = {
    "NH": {
        "connected_speech": "isolated words or one memorized sentence",
        "total_words_anchor": {"typical": 6, "max": 10},
        "sentence_count_anchor": {"typical": 0, "max": 1},
        "summary": (
            "Speaks mostly in isolated words; around 6 words total or one memorized sentence; "
            "little or no connected sentence production."
        ),
    },
    "IL": {
        "connected_speech": "simple sentences",
        "total_words_anchor": {"min": 15, "max": 30, "typical": 22},
        "sentence_count_anchor": {"min": 3, "max": 5, "typical": 4},
        "summary": (
            "Simple sentences; around 15–30 total words and ~4 short sentences; "
            "mostly sentence-level production."
        ),
    },
    "IM1": {
        "connected_speech": "sentence units with basic communication",
        "total_words_anchor": {"min": 40, "max": 60, "typical": 50},
        "sentence_count_anchor": {"min": 6, "max": 10, "typical": 8},
        "summary": (
            "Sentence units; around 40–60 total words and ~8 sentences; "
            "basic communication, limited detail."
        ),
    },
    "IM2": {
        "connected_speech": "groups of sentences, still basic structure",
        "total_words_anchor": {"min": 60, "max": 80, "typical": 70},
        "sentence_count_anchor": {"min": 8, "max": 12, "typical": 10},
        "summary": (
            "Groups of sentences; around 60–80 total words and ~10 sentences; "
            "understandable with some detail, but structure still basic."
        ),
    },
    "IM3": {
        "connected_speech": "paragraph-like development begins",
        "total_words_anchor": {"min": 80, "max": 100, "typical": 90},
        "sentence_count_anchor": {"min": 10, "max": 14, "typical": 12},
        "summary": (
            "Paragraph-like development; around 80–100 words and ~12 sentences; "
            "connectors and longer patterns appear; grammar/tense errors still visible."
        ),
    },
    "IH": {
        "connected_speech": "organized paragraph form",
        "total_words_anchor": {"min": 100, "max": 120, "typical": 110},
        "sentence_count_anchor": {"min": 12, "max": 16, "typical": 13},
        "summary": (
            "Paragraph form; around 100–120 words and 12+ sentences; organized, relevant, extended; "
            "connectors used well; solid Q3 roleplay; vocabulary beyond only like/good/many/very."
        ),
    },
    "AL": {
        "connected_speech": "strong paragraph, flexible and detailed",
        "total_words_anchor": {"min": 150, "typical": 160},
        "sentence_count_anchor": {"min": 18, "typical": 20},
        "summary": (
            "Strong paragraph; 150+ words and ~20 sentences; flexible, detailed, organized; "
            "attempts native-like or advanced expressions. Do not assign AL easily in 3-question mini."
        ),
    },
}

MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE: Tuple[str, ...] = (
    "1. First check response amount: total_word_count, total_sentence_count, "
    "total_duration_seconds if available, and connected speech level vs level anchors.",
    "2. Then check quality: relevance, structure, grammar, vocabulary, naturalness, roleplay.",
    "3. Do not assign IH/AL based only on word count.",
    "4. Do not assign IM3/IH if Q3 roleplay fails badly.",
    "5. IL–IM2: prioritize sentence production and answer length over advanced vocabulary.",
    "6. IM3–IH: require connector use, longer sentence patterns, paragraph-like development.",
    "7. AL: requires strong detail, organization, flexibility, more native-like expressions — rare in mini mock.",
)

MINI_MOCK_V2_ROLEPLAY_GATE: str = (
    "Q3 ROLEPLAY GATE: If the prompt asks the student to speak to another person or ask questions, "
    "the answer must directly address that person, complete the roleplay task, include 2–3 natural "
    "questions when required, and sound conversational. If Q3 roleplay is weak or off-task, do not "
    "give IH or AL overall — even if Q1/Q2 are long, cap at IM3 unless overall performance clearly compensates."
)

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

# Used by analysis.py for connector_count metric only (not level scoring logic).
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
    "IL–IM2 단계에서는 고급 어휘보다 완성된 문장을 더 많이 만드는 것이 우선입니다.",
    "IH 이상을 목표로 하려면 Q3에서 상대에게 자연스럽게 질문하고 대안을 제시하는 능력이 필요합니다.",
)

# Backward-compatible aliases (prefer MINI_MOCK_V2_* names in new code).
DURATION_CONTEXT = MINI_MOCK_V2_DURATION_CONTEXT
WPM_RULES = MINI_MOCK_V2_WPM_RULES
LEVEL_DECISION_GUIDANCE = MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE
ROLEPLAY_GATE = MINI_MOCK_V2_ROLEPLAY_GATE
VOCABULARY_RULES = MINI_MOCK_V2_VOCABULARY_RULES
CONNECTOR_RULES = MINI_MOCK_V2_CONNECTOR_RULES
FEEDBACK_STYLE_EXAMPLES = MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES


def format_level_rules_for_prompt() -> str:
    """Serialize all level calibration rules for Gemini rubric injection."""
    block = {
        "level_rule_version": LEVEL_RULE_VERSION,
        "levels": MINI_MOCK_V2_LEVEL_RULES,
        "duration_context": MINI_MOCK_V2_DURATION_CONTEXT,
        "wpm_rules": MINI_MOCK_V2_WPM_RULES,
        "decision_guidance": list(MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE),
        "roleplay_gate": MINI_MOCK_V2_ROLEPLAY_GATE,
        "vocabulary_rules": MINI_MOCK_V2_VOCABULARY_RULES,
        "connector_rules": MINI_MOCK_V2_CONNECTOR_RULES,
    }
    return json.dumps(block, ensure_ascii=False, indent=2)
