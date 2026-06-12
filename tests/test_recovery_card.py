"""Unit tests for recovery card markup."""

import unittest

from components.recovery_card import (
    ANALYSIS_RECOVERY_TITLE,
    render_analysis_recovery_card,
    render_recovery_card_html,
)


class TestRecoveryCard(unittest.TestCase):
    def test_analysis_recovery_card(self):
        html_out = render_analysis_recovery_card(
            meta_html="<span>시도 횟수 2회</span>",
        )
        self.assertIn('class="recovery-card"', html_out)
        self.assertIn('class="rv-stage"', html_out)
        self.assertIn('M44 47 Q49 44 54 47', html_out)
        self.assertIn(ANALYSIS_RECOVERY_TITLE, html_out)
        self.assertIn("rv-emphasis", html_out)
        self.assertIn("시도 횟수 2회", html_out)

    def test_compact_card(self):
        html_out = render_recovery_card_html(
            eyebrow="테스트",
            title="제목",
            body_html="본문",
            character_size=72,
            compact=True,
        )
        self.assertIn("recovery-card--compact", html_out)
        self.assertIn('width="72"', html_out)


if __name__ == "__main__":
    unittest.main()
