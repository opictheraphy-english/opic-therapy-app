"""Script Coaching metrics — re-export from script_coaching_text_metrics (import stability)."""

from services.script_coaching_text_metrics import (  # noqa: F401
    SCRIPT_CONNECTOR_MARKERS,
    SCRIPT_WORD_ANCHORS,
    build_script_text_metrics,
    count_connectors,
    count_sentences,
    count_vague_words,
    count_words,
    response_amount_score_from_word_count,
    word_count_level_hint,
)
