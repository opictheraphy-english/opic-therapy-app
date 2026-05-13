"""MIME guess for inline audio bytes (WAV / WebM / MP3)."""


def guess_audio_mime(audio_bytes: bytes) -> str:
    """인라인 오디오 파트용 MIME 추정 (WAV / WebM / MP3 등)."""
    if not audio_bytes or len(audio_bytes) < 12:
        return "audio/wav"
    if audio_bytes[:4] == b"RIFF":
        return "audio/wav"
    if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm"
    if audio_bytes[:3] == b"ID3" or (
        len(audio_bytes) >= 2 and audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3")
    ):
        return "audio/mpeg"
    return "audio/wav"
