"""Static question MP3 assets — shared lookup for topic practice and mock v2."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
QUESTION_AUDIO_DIR = _ROOT / "assets" / "question_audio"
_MIN_MP3_BYTES = 64
MOCK_V2_INTRO_AUDIO_ID = "mock_v2_intro"


def load_question_mp3_bytes(audio_id: str) -> bytes | None:
    """Return MP3 bytes for ``audio_id`` when ``assets/question_audio/{id}.mp3`` exists."""
    key = str(audio_id or "").strip()
    if not key:
        return None
    path = QUESTION_AUDIO_DIR / f"{key}.mp3"
    if not path.is_file():
        return None
    try:
        blob = path.read_bytes()
    except OSError:
        return None
    if len(blob) < _MIN_MP3_BYTES:
        return None
    return blob


def mock_v2_question_audio_id(q: dict) -> str:
    """Resolve the MP3 filename stem for a mock_v2 exam question dict."""
    if not isinstance(q, dict):
        return ""
    source_id = str(q.get("source_id") or "").strip()
    if source_id:
        return source_id
    combo = str(q.get("combo") or "").strip()
    if combo == "Intro":
        return MOCK_V2_INTRO_AUDIO_ID
    step = str(q.get("step") or "").strip()
    topic = str(q.get("topic") or "").strip()
    if combo == "Advanced" and topic:
        if step == "Comparison":
            return f"{topic}_comparison"
        if step == "News/Issue":
            return f"{topic}_news_issue"
    return ""
