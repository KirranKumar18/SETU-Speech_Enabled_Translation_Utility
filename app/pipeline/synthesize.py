import os
import logging
from typing import Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger("setu.synthesize")

GCP_VOICE_MAPPING = {
    "hi": {"language_code": "hi-IN", "name": "hi-IN-Neural2-B"},
    "ta": {"language_code": "ta-IN", "name": "ta-IN-Standard-A"},
    "te": {"language_code": "te-IN", "name": "te-IN-Standard-A"},
    "kn": {"language_code": "kn-IN", "name": "kn-IN-Standard-A"},
    "mr": {"language_code": "mr-IN", "name": "mr-IN-Standard-A"},
    "bn": {"language_code": "bn-IN", "name": "bn-IN-Standard-A"},
    "gu": {"language_code": "gu-IN", "name": "gu-IN-Standard-A"},
    "ml": {"language_code": "ml-IN", "name": "ml-IN-Standard-A"},
    "pa": {"language_code": "pa-IN", "name": "pa-IN-Standard-A"},
    "en": {"language_code": "en-IN", "name": "en-IN-Neural2-B"}
}

def synthesize_with_gcp(text: str, language_code: str, output_path: str) -> bool:
    """Synthesize audio using Google Cloud Text-to-Speech API."""
    cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path or not os.path.exists(cred_path):
        return False

    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_config = GCP_VOICE_MAPPING.get(language_code, {"language_code": "hi-IN", "name": "hi-IN-Standard-A"})
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["language_code"],
            name=voice_config.get("name")
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,
            pitch=0.0
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        logger.info(f"Synthesized audio using Google Cloud TTS -> {output_path}")
        return True
    except Exception as e:
        logger.warning(f"Google Cloud TTS synthesis failed ({e}). Defaulting to gTTS fallback.")
        return False

def synthesize_with_gtts(text: str, language_code: str, output_path: str) -> bool:
    """Synthesize audio using gTTS (Google Translate TTS package)."""
    try:
        from gtts import gTTS
        # gtts uses two-letter language codes
        lang = language_code if language_code != "or" else "hi"
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        logger.info(f"Synthesized audio using gTTS fallback -> {output_path}")
        return True
    except Exception as e:
        logger.error(f"gTTS synthesis failed for lang {language_code}: {e}")
        return False

def synthesize_speech(text: str, station_code: str, platform_number: str, language_code: str) -> Tuple[str, str]:
    """
    Synthesize translated text to speech mp3 file and save in static/audio.
    Returns (relative_file_path, synthesis_engine_name).
    """
    st_code = station_code.strip().upper()
    p_num = platform_number.strip().upper()
    lang = language_code.strip().lower()

    filename = f"{st_code}_P{p_num}_{lang}.mp3"
    full_path = str(settings.AUDIO_DIR / filename)
    relative_path = f"audio/{filename}"

    # Try GCP TTS first
    success = synthesize_with_gcp(text, lang, full_path)
    engine_used = "GoogleCloudTTS"

    # Fall back to gTTS
    if not success:
        success = synthesize_with_gtts(text, lang, full_path)
        engine_used = "gTTS"

    if not success:
        raise RuntimeError(f"All TTS synthesis engines failed for language {language_code}")

    return relative_path, engine_used
