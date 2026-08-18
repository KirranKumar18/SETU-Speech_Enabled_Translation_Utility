import os
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.cache.audio_cache import (
    save_announcement,
    save_cached_audio,
    list_all_announcements,
    get_cached_audio
)
from app.pipeline.transcribe import transcribe_audio_bytes
from app.pipeline.translate import translate_text, translate_to_all_supported_languages
from app.pipeline.synthesize import synthesize_speech
from app.config import settings

logger = logging.getLogger("setu.routes.announcements")

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

class TestSynthesisRequest(BaseModel):
    text: str
    target_lang: str
    station_code: str = "DEMO"
    platform_number: str = "1"

@router.post("/upload")
async def upload_announcement(
    station_code: str = Form(...),
    platform_number: str = Form(...),
    transcript: Optional[str] = Form(None),
    source_language: Optional[str] = Form("en"),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    Upload an audio announcement file or provide text.
    Processes STT -> Multilingual Translation -> TTS Synthesis -> SQLite Cache.
    """
    station_code = station_code.strip().upper()
    platform_number = platform_number.strip().upper()

    final_transcript = ""

    # Handle file upload and Speech-to-Text transcription if provided
    if audio_file:
        try:
            contents = await audio_file.read()
            if len(contents) > 0:
                stt_res = transcribe_audio_bytes(contents, filename=f"upload_{audio_file.filename}")
                final_transcript = stt_res.get("text", "").strip()
        except Exception as e:
            logger.error(f"Error processing audio upload STT: {e}")

    # Fall back to form transcript if file wasn't provided or yielded empty text
    if not final_transcript and transcript:
        final_transcript = transcript.strip()

    if not final_transcript:
        # Default placeholder demo announcement if neither audio nor text was provided
        final_transcript = f"Attention passengers: Train number 12951 Express to Mumbai Central is arriving on platform number {platform_number}."

    # 1. Save original announcement record in SQLite DB
    announcement = save_announcement(
        station_code=station_code,
        platform_number=platform_number,
        original_transcript=final_transcript,
        source_language=source_language
    )

    # 2. Translate into supported languages
    translations = translate_to_all_supported_languages(final_transcript, source_lang=source_language)
    
    # Always include source transcript for English/Original
    if source_language not in translations:
        translations[source_language] = final_transcript

    cached_results = []

    # 3. Synthesize speech for each language and store in cache
    for lang_code, translated_text in translations.items():
        try:
            rel_audio_path, engine_used = synthesize_speech(
                text=translated_text,
                station_code=station_code,
                platform_number=platform_number,
                language_code=lang_code
            )

            cache_record = save_cached_audio(
                announcement_id=announcement.id,
                station_code=station_code,
                platform_number=platform_number,
                language_code=lang_code,
                translated_text=translated_text,
                audio_file_path=rel_audio_path,
                synthesis_engine=engine_used
            )

            cached_results.append({
                "language_code": lang_code,
                "language_name": settings.SUPPORTED_LANGUAGES.get(lang_code, lang_code.upper()),
                "translated_text": translated_text,
                "audio_url": f"{settings.BASE_URL}/static/{rel_audio_path}",
                "audio_file_path": rel_audio_path,
                "synthesis_engine": engine_used
            })
        except Exception as e:
            logger.error(f"Failed processing language '{lang_code}': {e}")

    return {
        "status": "success",
        "message": f"Processed and cached announcement for station {station_code}, platform {platform_number}.",
        "announcement": {
            "id": announcement.id,
            "station_code": announcement.station_code,
            "platform_number": announcement.platform_number,
            "original_transcript": announcement.original_transcript,
            "source_language": announcement.source_language,
            "cached_translations": cached_results
        }
    }

@router.get("")
async def get_announcements():
    """Retrieve all announcements and their cached translated audio files."""
    data = list_all_announcements()
    # Format full URLs for audio
    for ann in data:
        for trans in ann.get("cached_translations", []):
            trans["audio_url"] = f"{settings.BASE_URL}/static/{trans['audio_file_path']}"
    return {"status": "success", "count": len(data), "announcements": data}

@router.post("/test-synthesis")
async def test_synthesis(req: TestSynthesisRequest):
    """On-the-fly single language translation and speech synthesis test."""
    translated = translate_text(req.text, target_lang=req.target_lang)
    rel_path, engine = synthesize_speech(
        text=translated,
        station_code=req.station_code,
        platform_number=req.platform_number,
        language_code=req.target_lang
    )

    return {
        "status": "success",
        "original_text": req.text,
        "target_lang": req.target_lang,
        "translated_text": translated,
        "audio_url": f"{settings.BASE_URL}/static/{rel_path}",
        "engine": engine
    }
