import os
import logging
from typing import Dict, Any, Tuple
from app.config import settings

import re

logger = logging.getLogger("setu.synthesize")

DIGIT_WORDS = {
    "hi": {"0": "शून्य", "1": "एक", "2": "दो", "3": "तीन", "4": "चार", "5": "पांच", "6": "छह", "7": "सात", "8": "आठ", "9": "नौ"},
    "ta": {"0": "பூஜ்ஜியம்", "1": "ஒன்று", "2": "இரண்டு", "3": "மூன்று", "4": "நான்கு", "5": "ஐந்து", "6": "ஆறு", "7": "ஏழு", "8": "எட்டு", "9": "ஒன்பது"},
    "te": {"0": "సున్నా", "1": "ఒకటి", "2": "రెండు", "3": "మూడు", "4": "నాలుగు", "5": "ఐదు", "6": "ఆరు", "7": "ఏడు", "8": "ఎనిమిది", "9": "తొమ్మిది"},
    "kn": {"0": "ಸೊನ್ನೆ", "1": "ಒಂದು", "2": "ಎರಡು", "3": "ಮೂರು", "4": "ನಾಲ್ಕು", "5": "ಐದು", "6": "ಆರು", "7": "ಏಳು", "8": "ಎಂಟು", "9": "ಒಂಬತ್ತು"},
    "mr": {"0": "शून्य", "1": "एक", "2": "दोन", "3": "तीन", "4": "चार", "5": "पाच", "6": "सहा", "7": "सात", "8": "आठ", "9": "नऊ"},
    "bn": {"0": "শূন্য", "1": "এক", "2": "দুই", "3": "তিন", "4": "চার", "5": "পাঁচ", "6": "ছয়", "7": "সাত", "8": "আট", "9": "নয়"},
    "gu": {"0": "શૂન્ય", "1": "એક", "2": "બે", "3": "ત્રણ", "4": "ચાર", "5": "પાંચ", "6": "છ", "7": "સાત", "8": "આઠ", "9": "નવ"},
    "ml": {"0": "പൂജ്യം", "1": "ഒന്ന്", "2": "രണ്ട്", "3": "മൂന്ന്", "4": "നാല്", "5": "അഞ്ച്", "6": "ആറ്", "7": "ഏഴ്", "8": "എട്ട്", "9": "ഒൻപത്"},
    "pa": {"0": "ਸਿਫ਼ਰ", "1": "ਇੱਕ", "2": "ਦੋ", "3": "ਤਿੰਨ", "4": "ਚਾਰ", "5": "ਪੰਜ", "6": "ਛੇ", "7": "ਸੱਤ", "8": "ਅੱਠ", "9": "ਨੌਂ"},
    "en": {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
}

# Indic numerals map to ASCII digits
INDIC_NUMERALS_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
    '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4', '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',
    '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4', '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    '୦': '0', '୧': '1', '୨': '2', '୩': '3', '୪': '4', '୫': '5', '୬': '6', '୭': '7', '୮': '8', '୯': '9',
    '௦': '0', '੧': '1', '௨': '2', '௩': '3', '௪': '4', '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',
    '౦': '0', '౧': '1', '౨': '2', '౩': '3', '౪': '4', '౫': '5', '౬': '6', '౭': '7', '౮': '8', '౯': '9',
    '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
    '൦': '0', '൧': '1', '൨': '2', '൩': '3', '൪': '4', '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9',
}

def format_speech_digits(text: str, language_code: str) -> str:
    """
    Converts numbers in text to digit-by-digit words for standard railway announcement pronunciation.
    e.g. 12951 -> 'एक दो नौ पांच एक' (Hindi) or 'ஒன்று இரண்டு ஒன்பது ஐந்து ஒன்று' (Tamil)
    """
    lang = language_code.lower()
    words_map = DIGIT_WORDS.get(lang, DIGIT_WORDS["en"])

    # First normalize any Indic script numerals to ASCII digits
    normalized_text = ""
    for char in text:
        normalized_text += INDIC_NUMERALS_MAP.get(char, char)

    # Convert multi-digit numbers (like train numbers, 2+ digits) to spoken digit words
    def digit_replacer(match):
        digits = match.group(0)
        return " " + " ".join([words_map.get(d, d) for d in digits]) + " "

    # Replace 2+ digit numbers (like train numbers 12951, platform 12, etc.)
    return re.sub(r'\b\d{2,}\b', digit_replacer, normalized_text).strip()

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

import hashlib

def synthesize_speech(text: str, station_code: str, platform_number: str, language_code: str) -> Tuple[str, str]:
    """
    Synthesize translated text to speech mp3 file and save in static/audio.
    Uses content-based hashing so each unique announcement gets its own audio file.
    Returns (relative_file_path, synthesis_engine_name).
    """
    st_code = station_code.strip().upper()
    p_num = platform_number.strip().upper()
    lang = language_code.strip().lower()

    # Format numbers into digit-by-digit speech pronunciation (e.g. 12951 -> 'एक दो नौ पांच एक')
    speech_text = format_speech_digits(text, lang)

    # Content-based hash ensures every unique text generates its own unique audio file
    content_hash = hashlib.md5(speech_text.encode("utf-8")).hexdigest()[:8]
    filename = f"{st_code}_P{p_num}_{lang}_{content_hash}.mp3"
    full_path = str(settings.AUDIO_DIR / filename)
    relative_path = f"audio/{filename}"

    # If already synthesized for this exact text content on disk, reuse immediately
    if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
        return relative_path, "Cached Audio"

    # Try GCP TTS first
    success = synthesize_with_gcp(speech_text, lang, full_path)
    engine_used = "GoogleCloudTTS"

    # Fall back to gTTS
    if not success:
        success = synthesize_with_gtts(speech_text, lang, full_path)
        engine_used = "gTTS"

    if not success:
        raise RuntimeError(f"All TTS synthesis engines failed for language {language_code}")

    return relative_path, engine_used
