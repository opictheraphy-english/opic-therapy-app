"""Static checks for IH/AL rubric recalibration (shared level_rules)."""

from __future__ import annotations

import json

from services.mini_mock_v2_level_rules import (
    ADVANCED_FUNCTION_GATE,
    ANCHOR_USAGE_NOTE,
    DELIVERY_QUALITY_GUIDANCE,
    LEVEL_ANTI_DEFLATION_GUIDANCE,
    MINI_MOCK_V2_LEVEL_RULES,
    MINI_MOCK_V2_WPM_RULES,
    LEVEL_RULE_VERSION,
    format_level_rules_for_prompt,
)
from tools.check_openai_mock_v2_report import (
    _im_low_regression_answers,
    _question_bank,
    _real_ih_q14_san_diego_transcript,
    _real_ih_san_diego_answers,
    _validate_im_low_level,
    _validate_real_ih_level,
)


def test_level_rule_version_bumped():
    assert "ih_al_recalibration" in LEVEL_RULE_VERSION


def test_al_summary_no_suppression():
    al = MINI_MOCK_V2_LEVEL_RULES["AL"]["summary"]
    assert "Do not assign AL easily" not in al
    assert "withhold al" in al.lower()


def test_ih_summary_accepts_fillers():
    ih = MINI_MOCK_V2_LEVEL_RULES["IH"]["summary"]
    assert "um" in ih.lower() or "uh" in ih.lower()
    assert "do not downgrade" in ih.lower() or "do not" in ih.lower()


def test_advanced_gate_roleplay_scoped():
    gate = ADVANCED_FUNCTION_GATE.lower()
    assert "mode a" in gate
    assert "mode b" in gate
    assert "non-roleplay" in gate
    assert "complication" in gate


def test_delivery_and_anti_deflation_in_prompt_json():
    blob = format_level_rules_for_prompt()
    data = json.loads(blob)
    assert "delivery_quality_guidance" in data
    assert "level_anti_deflation_guidance" in data
    assert "minor fillers" in data["level_anti_deflation_guidance"].lower()


def test_anchor_usage_soft_language():
    note = ANCHOR_USAGE_NOTE.lower()
    assert "typical reference" in note
    assert "hard" in note and "gate" in note


def test_wpm_rules_support_combined_signal():
    cap = MINI_MOCK_V2_WPM_RULES["overall_level_cap"]
    assert "110" in cap
    assert "never" in cap.lower()


def test_real_ih_q14_word_and_duration_profile():
    text = _real_ih_q14_san_diego_transcript()
    words = len(text.split())
    assert 200 <= words <= 260, f"expected ~230 words, got {words}"
    assert "has has uh has" in text


def test_real_ih_sample_q14_metrics():
    questions = _question_bank()
    rows = _real_ih_san_diego_answers(questions)
    q14 = next(r for r in rows if r["opic_type"] == "Comparison")
    assert q14["duration_seconds"] == 110.0
    assert q14["wpm"] >= 110


def test_calibration_gate_helpers():
    assert _validate_real_ih_level("IH")[0]
    assert _validate_real_ih_level("IM3")[0]
    assert not _validate_real_ih_level("IM2")[0]
    assert _validate_im_low_level("IM2")[0]
    assert not _validate_im_low_level("IH")[0]


def test_im_low_sample_is_short_list_like():
    questions = _question_bank()
    rows = _im_low_regression_answers(questions)
    assert all(len(r["transcript"].split()) < 25 for r in rows)
