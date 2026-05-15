"""Server-side TTS: Cloud Neural2 → gTTS → macOS say."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from io import BytesIO
from typing import Any, Dict

import streamlit as st

logger = logging.getLogger(__name__)

NEURAL2_EVA = "en-US-Neural2-F"
NEURAL2_DANIEL = "en-US-Neural2-H"
DEFAULT_TTS_SPEAKING_RATE = 0.95
DEFAULT_TTS_PITCH = 0.0


def neural2_voice_for_choice(voice_choice: str) -> str:
    return NEURAL2_DANIEL if voice_choice == "Daniel" else NEURAL2_EVA


def neural2_voice_for_session() -> str:
    preset = st.session_state.get("voice_choice", "Eva")
    return neural2_voice_for_choice(str(preset))


def load_texttospeech_module():
    try:
        from google.cloud import texttospeech as tts_module

        return tts_module
    except Exception:
        try:
            from google.cloud import texttospeech_v1 as tts_module

            return tts_module
        except Exception:
            return None


def gcp_credentials_for_tts():
    raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not raw:
        try:
            raw = st.secrets.get("GCP_SERVICE_ACCOUNT_JSON")
        except Exception:
            raw = None
    if not raw:
        return None
    try:
        if isinstance(raw, dict):
            info = raw
        else:
            info = json.loads(raw)
        if not isinstance(info, dict) or info.get("type") != "service_account":
            return None
        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_info(info)
    except Exception as e:
        logger.warning("GCP service account JSON parse failed: %s: %s", type(e).__name__, e)
        return None


def synthesize_gtts_mp3(text: str) -> bytes:
    from gtts import gTTS

    if not (text or "").strip():
        raise ValueError("TTS text is empty")
    fp = BytesIO()
    gTTS(text=text, lang="en", slow=False).write_to_fp(fp)
    data = fp.getvalue()
    if not data or len(data) < 64:
        raise RuntimeError("gTTS returned empty or too-small audio")
    return data


def synthesize_with_macos_say(text: str) -> bytes:
    voice_candidates = ["Samantha", "Allison", "Ava", "Alex"]
    last_err = None
    for voice in voice_candidates:
        tmp_aiff = None
        tmp_wav = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
                tmp_aiff = tmp.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_wav = tmp.name

            say_cmd = ["say", "-v", voice, "-r", "190", "-o", tmp_aiff, text]
            subprocess.run(say_cmd, check=True, capture_output=True, text=True)

            convert_cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", tmp_aiff, tmp_wav]
            subprocess.run(convert_cmd, check=True, capture_output=True, text=True)

            with open(tmp_wav, "rb") as f:
                audio_bytes = f.read()
            if not audio_bytes:
                raise RuntimeError("macOS say produced empty wav bytes")
            return audio_bytes
        except Exception as e:
            last_err = e
        finally:
            for path in [tmp_aiff, tmp_wav]:
                if not path:
                    continue
                if not os.path.exists(path):
                    continue
                try:
                    os.remove(path)
                except Exception:
                    pass
    raise RuntimeError(f"macOS say fallback failed: {last_err}")


def synthesize_google_cloud_neural2(text: str, voice_name: str, speaking_rate: float, pitch: float) -> bytes:
    if not (text or "").strip():
        raise ValueError("TTS text is empty")
    tts_module = load_texttospeech_module()
    if tts_module is None:
        raise RuntimeError(
            "google-cloud-texttospeech 패키지가 없습니다. `pip install google-cloud-texttospeech`"
        )
    creds = gcp_credentials_for_tts()
    if creds is not None:
        client = tts_module.TextToSpeechClient(credentials=creds)
    else:
        client = tts_module.TextToSpeechClient()
    response = client.synthesize_speech(
        input=tts_module.SynthesisInput(text=text),
        voice=tts_module.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        ),
        audio_config=tts_module.AudioConfig(
            audio_encoding=tts_module.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        ),
    )
    content = response.audio_content
    if not content or len(content) < 64:
        raise RuntimeError("Cloud TTS returned empty audio")
    return content


def synthesize_tts_audio(
    text: str,
    voice_name: str = NEURAL2_EVA,
    speaking_rate: float = DEFAULT_TTS_SPEAKING_RATE,
    pitch: float = DEFAULT_TTS_PITCH,
) -> Dict[str, Any]:
    errs = []
    try:
        mp3 = synthesize_google_cloud_neural2(text, voice_name, speaking_rate, pitch)
        return {
            "audio_bytes": mp3,
            "audio_format": "audio/mp3",
            "engine": f"Google Cloud · {voice_name}",
        }
    except Exception as e:
        errs.append(f"Neural2: {e}")
        logger.info("Cloud Neural2 TTS skipped: %s: %s", type(e).__name__, e)

    try:
        mp3 = synthesize_gtts_mp3(text)
        return {
            "audio_bytes": mp3,
            "audio_format": "audio/mp3",
            "engine": "gTTS (네트워크 폴백)",
        }
    except Exception as e:
        errs.append(f"gTTS: {e}")
        logger.warning("gTTS fallback failed: %s: %s", type(e).__name__, e)

    if sys.platform == "darwin":
        try:
            wav = synthesize_with_macos_say(text)
            return {
                "audio_bytes": wav,
                "audio_format": "audio/wav",
                "engine": "macOS say (로컬 폴백)",
            }
        except Exception as e:
            errs.append(f"macOS: {e}")
            logger.warning("macOS say fallback failed: %s: %s", type(e).__name__, e)

    raise RuntimeError(
        "모든 TTS 경로가 실패했습니다. 다음을 확인하세요:\n"
        "· Google Cloud: `GCP_SERVICE_ACCOUNT_JSON` 환경변수 또는 secrets의 `GCP_SERVICE_ACCOUNT_JSON`에 서비스 계정 JSON\n"
        "· 또는 `gcloud auth application-default login` / `GOOGLE_APPLICATION_CREDENTIALS` 파일 경로\n"
        "· gTTS: 인터넷 연결 및 `pip install gTTS`\n"
        "· macOS: 로컬 `say` 명령 사용 가능 여부\n\n"
        + " | ".join(errs)
    )


@st.cache_data(show_spinner=False, max_entries=512)
def tts_audio_cached(text: str, voice_name: str, speaking_rate: float, pitch: float):
    return synthesize_tts_audio(text, voice_name, speaking_rate, pitch)


def speak_direct_macos(text: str, voice_name: str) -> None:
    if os.name != "posix":
        return
    preset = st.session_state.get("voice_choice", "Eva")
    say_voice_map = {
        "Eva": "Samantha",
        "Daniel": "Daniel",
    }
    rate_map = {
        "Eva": "190",
        "Daniel": "180",
    }
    say_voice = say_voice_map.get(str(preset), "Samantha")
    say_rate = rate_map.get(str(preset), "190")
    try:
        subprocess.Popen(["say", "-v", say_voice, "-r", say_rate, text])
    except Exception as e:
        logger.warning("direct macOS say failed: %s: %s", type(e).__name__, e)


def clear_mock_question_tts_keys() -> None:
    prefixes = (
        "_mock_q_tts_",
        "_mock_tts_pref_",
        "_mock_q_display_",
        "_mock_pref_fail_",
    )
    for k in list(st.session_state.keys()):
        if k.startswith(prefixes):
            del st.session_state[k]
