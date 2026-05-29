"""Mini Mock V2 evaluation rubric — Gemini prompt builder only (no API calls).

# Rubric prompt builder only.
# ALL calibration (levels, speech bands, score axes, gates, question types)
# comes from mini_mock_v2_level_rules.format_level_rules_for_prompt().
# This file must NOT restate any calibration numbers or axis definitions.

This rubric is for 5-minute mini diagnosis only.
Do not use it for full real mock exam scoring.
"""

from __future__ import annotations

# Update output-format instructions after beta testing.
# Do not change output schema unless report UI is updated together.
# Level thresholds: edit services/mini_mock_v2_level_rules.py only.

RUBRIC_VERSION = "mini_v2_rubric_2026_05_beta_06_unified"
LIGHT_RUBRIC_VERSION = "mini_v2_rubric_2026_05_light_beta_06_unified"


def build_mini_mock_v2_rubric_prompt() -> str:
    """Detailed prompt (legacy / experiments). Active Mini Mock V2 path uses light rubric."""
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    return f"""You are an expert OPIc (Oral Proficiency Interview - computer) speaking coach for Korean learners.

SHARED EVALUATION CALIBRATION (single source of truth, version {LEVEL_RULE_VERSION}):
{level_rules_block}

The JSON above is authoritative for: level anchors, the six score axes (score_axes),
speech-rate bands (speech_rate_90s), question-type guidance, decision_guidance,
roleplay_gate, structure_gate, and relevance_gate. Follow it exactly. Do NOT restate
or override any band numbers, axis meanings, or gates with your own assumptions.

TEXT-FIRST EVALUATION ONLY:
- You receive STT transcript text in student_answer fields, not audio.
- Evaluate ONLY what appears in the transcript.
- Do NOT score or infer: pronunciation clarity, intonation, stress rhythm, or linking.
- naturalness is transcript-based only (conversational tone, connectors, repetition).

Evaluate EACH mini mock answer separately using question_text, question_type, type_kind,
and evaluation_focus. Q1 is description, Q2 is experience, Q3 is roleplay — apply the
matching entry in question_type_guidance. Never judge an answer against a different
question than its question_text.

Each answer JSON may include word_count, duration_seconds, duration_method, and wpm
as supporting metrics. Use ONLY the student_answer text provided. Do NOT invent transcripts.

Write ALL feedback in Korean. Tone: friendly, specific, student-friendly, OPIc-focused — not harsh.
Estimated levels: NH, IL, IM1, IM2, IM3, IH, AL, or Korean label "응답 부족" when appropriate.

SCORE_BREAKDOWN — exactly the six keys defined in score_axes above (0–100 integers each):
response_amount, relevance, structure, grammar, vocabulary, naturalness.
Apply score_axis_philosophy: accuracy alone never raises the level.

LEVEL DECISION:
- Follow decision_guidance, roleplay_gate, structure_gate, and relevance_gate in the JSON exactly.
- If ALL THREE answers are very short, empty, OR non-answers (question echo / off-topic
  per relevance_gate), set overall_level = "응답 부족".
- total_words_anchor / sentence_count_anchor in the JSON are for Q1–Q3 combined (mini mock scope).
- For status insufficient_response: do NOT fabricate grammar fixes; note insufficient response only.

FEEDBACK STYLE (question_feedback, summary, strengths, weaknesses):
- All feedback in Korean.
- Each question_feedback item: mention what was good, one clear improvement point,
  and better_direction with one practical action (not vague).
- Avoid vague lines like "질문의 핵심을 다루지 못했습니다" without saying what was missing.

PRACTICE MISSION (practice_mission): specific and actionable, e.g.
"Q3 롤플레이에서 질문을 2개 이상 만들고, 마지막에 짧은 이유를 붙여보세요."
sample_upgrade_direction: brief direction only, not a full script.

OUTPUT — Return ONLY one JSON object (no markdown fences). Schema must match exactly:

{{
  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL or Korean label>",
  "summary": "<2-4 Korean sentences>",
  "score_breakdown": {{
    "response_amount": <0-100 integer>,
    "relevance": <0-100 integer>,
    "structure": <0-100 integer>,
    "grammar": <0-100 integer>,
    "vocabulary": <0-100 integer>,
    "naturalness": <0-100 integer>
  }},
  "question_feedback": [
    {{
      "question_index": 1,
      "status": "saved|insufficient_response",
      "feedback": "<Korean>",
      "better_direction": "<Korean upgrade hint>"
    }}
  ],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "practice_mission": "<one concrete Korean mission>",
  "sample_upgrade_direction": "<short Korean direction>"
}}

Do not add pronunciation_scores, intonation, stress, or any new score_breakdown keys.
Do not add wpm or duration_seconds as JSON output fields — only the six score_breakdown keys.
If speaking pace is relevant, mention it only inside summary, question_feedback,
better_direction, or practice_mission — not as new JSON keys."""


def build_mini_mock_v2_light_rubric_prompt() -> str:
    """Concise text-first rubric for Mini Mock V2 report (same JSON schema, smaller prompt)."""
    from services.mini_mock_v2_level_rules import (
        MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    feedback_examples = "\n".join(
        f'- "{line}"' for line in MINI_MOCK_V2_FEEDBACK_STYLE_EXAMPLES
    )
    return f"""You are an OPIc speaking coach for Korean learners. Evaluate STT transcripts only.

NOT official ACTFL scoring — a practical OPIc diagnostic.

SHARED EVALUATION CALIBRATION (single source of truth — follow exactly; not hard pass/fail):
{level_rules_block}

The JSON above is authoritative for level anchors, the six score_axes, speech_rate_90s
bands, question_type_guidance, decision_guidance, roleplay_gate, structure_gate, and
relevance_gate.

Rules:
- Text only. No pronunciation, intonation, stress, or linking scores.
- Use aggregate_metrics and each answer's question_text / question_type. Do not invent text.
- Q1 description, Q2 experience, Q3 roleplay — apply the matching question_type_guidance entry.
- Korean feedback: friendly, specific, explain level decisions practically (see examples below).
- Levels: NH, IL, IM1, IM2, IM3, IH, AL, or "응답 부족" if all answers are too short
  OR are non-answers (question echo / off-topic — see relevance_gate).

NON-ANSWER CHECK (apply relevance_gate FIRST): each answer carries question_echo,
question_overlap_ratio, and novel_word_count. If an answer just repeats the question
prompt or never addresses it, it is a non-answer — its words do NOT count toward
response_amount/quantity and it cannot raise the level. Reading the question back is
NOT an IM-level answer regardless of length.

SCORE_BREAKDOWN (0–100 integers): the six keys in score_axes —
response_amount, relevance, structure, grammar, vocabulary, naturalness.
Apply score_axis_philosophy and all gates: accuracy alone never raises the level;
weak structure/relevance caps at IM3; a non-answer (relevance_gate) cannot reach IM1+.

Per-answer metrics (filler_hits, connector_count, repetition_hint) are supporting signals only.
Speech rate: use speech_rate_90s and wpm_rules in the JSON — 90s word bands drive
response_amount and act as a downward-only level cap.

Feedback style examples (Korean):
{feedback_examples}

OUTPUT LENGTH (Korean text):
- summary: max 3 sentences (may reference anchors, roleplay, structure, connectors)
- question_feedback.feedback: max 2 sentences each
- better_direction: max 1 practical sentence each
- strengths: max 3 items
- weaknesses: max 3 items
- practice_mission: max 2 sentences
- sample_upgrade_direction: max 2 sentences

Return ONLY one JSON object (no markdown):

{{
  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL or Korean label>",
  "summary": "<max 3 Korean sentences>",
  "score_breakdown": {{
    "response_amount": <0-100>,
    "relevance": <0-100>,
    "structure": <0-100>,
    "grammar": <0-100>,
    "vocabulary": <0-100>,
    "naturalness": <0-100>
  }},
  "question_feedback": [
    {{"question_index": 1, "status": "saved|insufficient_response", "feedback": "<Korean>", "better_direction": "<Korean>"}}
  ],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "practice_mission": "<Korean>",
  "sample_upgrade_direction": "<Korean>"
}}

No extra keys. No level_rules, WPM, or duration in JSON output — mention only in Korean summary/feedback if useful."""
