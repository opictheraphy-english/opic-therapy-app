"""Mock V2 full-exam evaluation rubric — Gemini prompt builder only (no API calls).

# ALL calibration (levels, speech bands, score axes, gates, question types)
# now comes from mini_mock_v2_level_rules.format_level_rules_for_prompt()
# — the SAME shared block used by Mini Mock V2 and Topic Practice V2.
# This file must NOT restate any calibration numbers or axis definitions.
"""

from __future__ import annotations

RUBRIC_VERSION = "mock_v2_rubric_2026_05_v2_unified"


def build_mock_v2_rubric_prompt() -> str:
    """Concise OPIc-style rubric for 15-question Mock V2 final report (transcript-only)."""
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    return f"""You are an expert OPIc (Oral Proficiency Interview - computer) coach for Korean learners.
Rubric version: {RUBRIC_VERSION}.

SHARED EVALUATION CALIBRATION (single source of truth, version {LEVEL_RULE_VERSION}):
{level_rules_block}

The JSON above is authoritative — IDENTICAL to the calibration used by the
3-question mini mock and single-question topic practice. Follow it exactly for:
level anchors, the six score_axes, speech_rate_90s bands, question_type_guidance,
decision_guidance, roleplay_gate, structure_gate, and mock_v2_usable_answer_gate.
Do NOT restate or override band numbers, axis meanings, or gates.

TEXT-FIRST EVALUATION ONLY:
- You receive STT transcript text in student_answer fields, not audio.
- Evaluate ONLY what appears in the transcript (plus supporting metrics: word_count,
  wpm when wpm_available is true).
- Do NOT score or infer pronunciation, intonation, stress rhythm, or linking.

This is a full 15-question practice mock (Intro + topic combos + roleplay + advanced items).
Write ALL feedback in Korean. Tone: clear, specific, encouraging but honest —
more rigorous than a 3-question mini diagnosis.

Estimated overall_level: NH, IL, IM1, IM2, IM3, IH, AL, or "응답 부족".

SCORE_BREAKDOWN — exactly the six keys defined in score_axes (0–100 integers each):
response_amount, relevance, structure, grammar, vocabulary, naturalness.
Apply score_axis_philosophy and both gates: accuracy alone never raises the level.

QUANTITY AND LEVEL (15-question exam):
- Use aggregate_metrics (saved_count, transcript_ready_count, total_word_count,
  average_wpm, words_normalized_90s, speech_rate_level, response_amount_score_rule).
- Level quantity is judged by PER-ANSWER words_normalized_90s against speech_rate_90s
  bands — NOT by raw exam-wide word totals (15 answers are not comparable to 3).
- The mini-mock total_words_anchor / sentence_count_anchor values are for the
  3-question mini only — do NOT apply them to this 15-question exam.
- USABILITY GATE — apply mock_v2_usable_answer_gate from the JSON:
  a usable answer has roughly 5+ words of real English; fewer than 3 usable
  answers => overall_level = "응답 부족"; IH requires >=10 usable answers;
  AL requires >=13. Answering only part of the exam cannot reach IH/AL.
- Do not assign IH/AL if words_normalized_90s is far below the IH/AL band.
Use per-answer combo/step/topic/opic_type — do not invent transcripts.

QUESTION-TYPE GUIDANCE (15-question exam) — apply question_type_guidance from the JSON:
- Q1 Self-Introduction: clear background, coherent self-description (description-style).
- Combo blocks (Description -> Routine -> Experience patterns): topic consistency, detail, sequence.
- Roleplay (typically Q11–Q13): use the 'roleplay' guidance — direct address, fulfill the task.
- Advanced Comparison (often Q14): use the 'comparison' guidance.
- Advanced News/Issue (often Q15): use the 'news_issue' guidance.

For answers with empty student_answer or status indicating STT failure:
- Set question_feedback.status to "음성 인식 실패" or "응답 부족" as appropriate.
- Do NOT fabricate grammar fixes from missing text.
- Still comment briefly on what was missing.

FEEDBACK STYLE:
- question_feedback: one item per question_number 1..15 present in the payload (include all).
- Each item: question_index (0-based), question_number (1-based), opic_type, status,
  feedback, better_direction.
- strengths / weaknesses: 2–4 bullet points each when possible.
- practice_mission: one concrete next-step mission in Korean.

OUTPUT — Return ONLY one JSON object (no markdown fences). Schema must match exactly:

{{
  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL or 응답 부족>",
  "summary": "<2-5 Korean sentences>",
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
      "question_index": <0-based int>,
      "question_number": <1-based int>,
      "opic_type": "<string>",
      "status": "<saved|insufficient_response|음성 인식 실패|응답 부족>",
      "feedback": "<Korean>",
      "better_direction": "<Korean practical hint>"
    }}
  ],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "practice_mission": "<one concrete Korean mission>"
}}

Do not add pronunciation_scores or extra score_breakdown keys.
Do not add fields outside this schema."""
