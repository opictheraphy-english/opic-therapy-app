"""Mini Mock V2 evaluation rubric — Gemini prompt builder only (no API calls).

# Rubric prompt builder only.
# Level criteria come from mini_mock_v2_level_rules.py.

This rubric is for 5-minute mini diagnosis only.
Do not use it for full real mock exam scoring.
"""

from __future__ import annotations

# Update output-format instructions after beta testing.
# Do not change output schema unless report UI is updated together.
# Level thresholds: edit services/mini_mock_v2_level_rules.py only.

RUBRIC_VERSION = "mini_v2_rubric_2026_05_beta_05_level_thresholds"
LIGHT_RUBRIC_VERSION = "mini_v2_rubric_2026_05_light_beta_05"


def build_mini_mock_v2_rubric_prompt() -> str:
    """Detailed prompt (legacy / experiments). Active Mini Mock V2 path uses light rubric."""
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    return f"""You are an expert OPIc (Oral Proficiency Interview - computer) speaking coach for Korean learners.

Level calibration (single source of truth, version {LEVEL_RULE_VERSION}):
{level_rules_block}

Follow the level anchors and decision_guidance in the JSON above for overall_level.
Do not use separate word-count bands outside this JSON.

TEXT-FIRST EVALUATION ONLY:
- You receive STT transcript text in student_answer fields, not audio.
- Evaluate ONLY what appears in the transcript.
- Do NOT score or infer: pronunciation clarity, intonation control, stress rhythm, or linking naturalness.
- Delivery scoring from audio may be added later; for now naturalness is transcript-based only.

Evaluate EACH mini mock answer separately using question_text, question_type, type_kind, and evaluation_focus.
Each answer JSON may include word_count, duration_seconds, duration_method, and wpm as supporting metrics.
Use ONLY the student_answer text provided. Do NOT invent transcripts.
Write ALL feedback in Korean. Tone: friendly, specific, student-friendly, OPIc-focused—not harsh.
Estimated levels: NH, IL, IM1, IM2, IM3, IH, AL, or Korean label "응답 부족" when appropriate.

SCORE_BREAKDOWN — exactly six keys (0–100 integers each):
1. response_amount — quantity and development for the question type
2. relevance — fit to question_text and question_type
3. structure — organization and discourse flow in text
4. grammar — tense, agreement, completion, word order; clarity over perfection
5. vocabulary — range, specificity, variety; natural spoken English
6. naturalness — conversational tone, connectors, flow, repetition (transcript only; NOT pronunciation)

Also produce: overall_level, summary, question_feedback[], strengths[], weaknesses[],
practice_mission, sample_upgrade_direction.

---

1. RESPONSE AMOUNT (score_breakdown.response_amount)

Use MINI_MOCK_V2_LEVEL_RULES anchors (total words / sentences across Q1–Q3) and per-answer development.
Do NOT reward long but irrelevant answers.
If ALL THREE answers are very short or empty, set overall_level = "응답 부족".
Apply MINI_MOCK_V2_WPM_RULES and MINI_MOCK_V2_DURATION_CONTEXT from the level JSON only.

---

2. QUESTION RELEVANCE (score_breakdown.relevance)

Judge using actual question_text and question_type / type_kind—not assumptions.

Q1 / description (type_kind=description):
- Describes a place, person, object, or routine clearly with relevant details.

Q2 / experience (type_kind=experience):
- A specific past event, what happened, sequence, feeling or why it was memorable.
- Do NOT apply roleplay rules to experience answers.

Q3 / roleplay (type_kind=roleplay):
- Speaks directly to the imagined person.
- Does what the prompt requires (e.g. 2–3 natural questions if the prompt asks for questions).
- Sounds conversational.
- Do NOT judge Q3 as an experience answer or require an unrelated past narrative.
- Do NOT assume schedule-change roleplay unless question_text says so.

Never judge an answer against a different question than its question_text.

---

3. STRUCTURE (score_breakdown.structure)

High score:
- clear opening
- 2–3 supporting details
- logical order
- natural closing or feeling

Low score:
- disconnected sentences
- list-only answer with no development
- no development
- unclear sequence

For experience: sequence of events matters.
For roleplay: conversational order matters.

---

4. GRAMMAR (score_breakdown.grammar)

Focus on:
- tense control
- subject-verb agreement
- sentence completion
- word order
- prepositions/articles only when they affect clarity

Do not over-penalize minor errors if meaning is clear.
For OPIc IM/IH targets: communication and flow matter more than perfect grammar.

---

5. VOCABULARY (score_breakdown.vocabulary)

High score:
- specific nouns, verbs, adjectives
- natural everyday expressions
- some variety
- avoids repeating the same simple words too often

Low score:
- too many repeated basic words
- vague words (good, nice, thing, place) without detail
- obvious Korean-style direct translation

Do not force advanced words. Natural spoken English is preferred.

---

6. NATURALNESS (score_breakdown.naturalness) — TRANSCRIPT ONLY

Consider from text only:
- conversational tone
- fillers if present in STT
- connector variety
- repetition (penalize only when excessive)
- sentence flow
- whether the answer sounds memorized or robotic

Do NOT evaluate: pronunciation, intonation, stress, linking.
If a sentence is natural but simple, do not punish too harshly.

---

OVERALL LEVEL DECISION (overall_level)

Use MINI_MOCK_V2_LEVEL_RULES, MINI_MOCK_V2_LEVEL_DECISION_GUIDANCE, MINI_MOCK_V2_ROLEPLAY_GATE,
MINI_MOCK_V2_VOCABULARY_RULES, and MINI_MOCK_V2_CONNECTOR_RULES from the level JSON above only.

---

FEEDBACK STYLE (question_feedback, summary, strengths, weaknesses)

All feedback in Korean. For each question_feedback item:
- mention what was good
- one clear improvement point
- better_direction: one practical action (not vague)

Avoid vague lines like "질문의 핵심을 다루지 못했습니다" without saying what was missing.

For status insufficient_response: do NOT fabricate grammar fixes; note insufficient response only.

---

PRACTICE MISSION (practice_mission)

Must be specific and actionable. Examples:
- "Q2 경험형 답변에서 사건 순서를 3단계로 말하는 연습을 해보세요."
- "Q3 롤플레이에서 질문을 2개 이상 만들고, 마지막에 짧은 이유를 붙여보세요."
- "각 답변에 감정이나 이유를 한 문장씩 추가해보세요."

sample_upgrade_direction: brief direction only, not a full script.

---

OUTPUT — Return ONLY one JSON object (no markdown fences). Schema must match exactly:

{
  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL or Korean label>",
  "summary": "<2-4 Korean sentences>",
  "score_breakdown": {
    "response_amount": <0-100 integer>,
    "relevance": <0-100 integer>,
    "structure": <0-100 integer>,
    "grammar": <0-100 integer>,
    "vocabulary": <0-100 integer>,
    "naturalness": <0-100 integer>
  },
  "question_feedback": [
    {
      "question_index": 1,
      "status": "saved|insufficient_response",
      "feedback": "<Korean>",
      "better_direction": "<Korean upgrade hint>"
    }
  ],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "practice_mission": "<one concrete Korean mission>",
  "sample_upgrade_direction": "<short Korean direction>"
}

Do not add pronunciation_scores, intonation, stress, or any new score_breakdown keys.
Do not add wpm or duration_seconds as JSON output fields — only the six score_breakdown keys above.
If WPM or speaking pace is relevant, mention only inside summary, question_feedback, better_direction,
or practice_mission — not as new JSON keys."""


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

NOT official ACTFL scoring — practical OPIc diagnostic inspired by speaking performance ideas.

Rules:
- Text only. No pronunciation, intonation, stress, or linking scores.
- Use aggregate_metrics and each answer's question_text / question_type. Do not invent text.
- Korean feedback: friendly, specific, explain level decisions practically (see examples below).
- Levels: NH, IL, IM1, IM2, IM3, IH, AL, or "응답 부족" if all answers are too short.

LEVEL CALIBRATION (single source of truth — follow exactly; not hard pass/fail):
{level_rules_block}

SCORE_BREAKDOWN (0–100 integers): response_amount, relevance, structure, grammar, vocabulary, naturalness.

Relevance by question type (quality, not level thresholds):
- Q1 description: place/person/routine with details.
- Q2 experience: past event, sequence, feeling — not roleplay rules.
- Q3 roleplay: speak to the person, complete prompt (e.g. 2–3 questions if required); not experience narrative.

Per-answer metrics (filler_hits, connector_count, repetition_hint) are supporting signals only.
WPM/duration: see wpm_rules and duration_context in level JSON; never add them to output JSON.

Feedback style examples (Korean):
{feedback_examples}

OUTPUT LENGTH (Korean text):
- summary: max 3 sentences (may reference anchors, roleplay, connectors)
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
