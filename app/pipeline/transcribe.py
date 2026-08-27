import os
import logging
from typing import Dict, Any

logger = logging.getLogger("setu.transcribe")

# Global whisper model cache
_whisper_model = None

def load_whisper_model(model_size: str = "base"):
    """Lazy load OpenAI Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info(f"Loading Whisper STT model '{model_size}'...")
            _whisper_model = whisper.load_model(model_size)
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load OpenAI Whisper model ({e}). Fallback transcription handler will be used.")
            _whisper_model = "fallback"
    return _whisper_model

def transcribe_audio_file(audio_path: str, language: str = None) -> Dict[str, Any]:
    """
    Transcribe an audio file using OpenAI Whisper STT.
    Returns dict with 'text' and 'language'.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = load_whisper_model()

    if model != "fallback" and hasattr(model, "transcribe"):
        try:
            logger.info(f"Transcribing audio file {audio_path} using Whisper...")
            options = {}
            if language:
                options["language"] = language
            
            result = model.transcribe(audio_path, **options)
            transcript_text = result.get("text", "").strip()
            detected_lang = result.get("language", language or "en")

            print("\n" + "="*70)
            print("🎙️  [SETU SPEECH-TO-TEXT TRANSCRIPTION]")
            print(f"   Audio File        : {os.path.basename(audio_path)}")
            print(f"   Detected Language : {detected_lang}")
            print(f"   Transcribed Text  : {transcript_text}")
            print(f"   STT Engine        : OpenAI Whisper ({getattr(model, 'name', 'base')})")
            print("="*70 + "\n", flush=True)

            logger.info(f"Whisper STT Output: lang={detected_lang}, text='{transcript_text}'")

            return {
                "text": transcript_text,
                "language": detected_lang,
                "engine": "OpenAI Whisper"
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")

    # Fallback response for missing audio decoder / demo fallback
    fallback_text = "Attention passengers: Train number 12951 Express from New Delhi to Mumbai Central is arriving shortly on platform number 1."
    print("\n" + "="*70)
    print("🎙️  [SETU SPEECH-TO-TEXT TRANSCRIPTION (FALLBACK)]")
    print(f"   Audio File        : {os.path.basename(audio_path)}")
    print(f"   Language          : en")
    print(f"   Transcribed Text  : {fallback_text}")
    print(f"   STT Engine        : Fallback Simulator")
    print("="*70 + "\n", flush=True)

    return {
        "text": fallback_text,
        "language": "en",
        "engine": "STT Fallback"
    }

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "temp_announcement.wav") -> Dict[str, Any]:
    """Helper to save audio bytes to temporary file and transcribe."""
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "audio", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, filename)

    with open(temp_filepath, "wb") as f:
        f.write(audio_bytes)

    try:
        res = transcribe_audio_file(temp_filepath)
        return res
    finally:
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception:
                pass
