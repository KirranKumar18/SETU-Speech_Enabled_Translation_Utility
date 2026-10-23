import os
import hashlib
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.cache.audio_cache import (
    save_announcement,
    save_cached_audio,
    list_all_announcements,
    get_cached_audio,
    find_announcement_by_transcript
)
from app.pipeline.transcribe import transcribe_audio_bytes
from app.pipeline.translate import translate_text, translate_to_all_supported_languages
from app.pipeline.synthesize import synthesize_speech
from app.config import settings

logger = logging.getLogger("setu.routes.announcements")

# In-memory set of transcript hashes currently being processed to prevent
# concurrent duplicate work when rapid polls arrive at the same time
_processing_lock = set()

def _transcript_hash(text: str) -> str:
    """Return a stable hash for a normalized transcript string."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:32]

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

class TestSynthesisRequest(BaseModel):
    text: str
    target_lang: str
    station_code: str = "DEMO"
    platform_number: str = "1"

class RTASyncRequest(BaseModel):
    station_code: str
    platform_number: Optional[str] = "1"
    transcript: str
    source_language: Optional[str] = "en"
    is_alert: Optional[bool] = False
    alert_priority: Optional[str] = "NORMAL"
    announcement_type: Optional[str] = "regular"

@router.post("/upload")
async def upload_announcement(
    station_code: str = Form(...),
    platform_number: Optional[str] = Form("1"),
    transcript: Optional[str] = Form(None),
    source_language: Optional[str] = Form("en"),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    Upload an audio announcement file or provide text.
    Processes STT -> Multilingual Translation -> TTS Synthesis -> SQLite Cache.
    """
    station_code = station_code.strip().upper()
    platform_number = platform_number.strip().upper() if platform_number else "1"

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

    print("\n" + "="*70)
    print("📢  [SETU NEW ANNOUNCEMENT RECEIVED]")
    print(f"   Station Code    : {station_code}")
    print(f"   Platform Number : {platform_number}")
    print(f"   Source Language : {source_language}")
    print(f"   Full Transcript : \"{final_transcript}\"")
    print("="*70 + "\n", flush=True)

    logger.info(f"Processing announcement for {station_code} P{platform_number}: '{final_transcript}'")

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
    # Format full URLs for audio and add language display names
    for ann in data:
        for trans in ann.get("cached_translations", []):
            trans["audio_url"] = f"{settings.BASE_URL}/static/{trans['audio_file_path']}"
            trans["language_name"] = settings.SUPPORTED_LANGUAGES.get(
                trans.get("language_code", ""), trans.get("language_code", "").upper()
            )
    return {"status": "success", "count": len(data), "announcements": data}

@router.post("/voice-transcribe")
async def voice_transcribe(
    audio_file: UploadFile = File(...)
):
    """
    Accept a voice recording from the browser microphone,
    run Speech-to-Text transcription via Whisper, and return the text.
    This powers the 'Voice Input' button on the Text Input tab.
    """
    try:
        contents = await audio_file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file received.")

        stt_result = transcribe_audio_bytes(contents, filename=f"voice_{audio_file.filename}")
        transcript = stt_result.get("text", "").strip()
        detected_lang = stt_result.get("language", "en")
        engine = stt_result.get("engine", "unknown")

        logger.info(f"Voice transcription complete: lang={detected_lang}, engine={engine}, text='{transcript}'")

        return {
            "status": "success",
            "transcript": transcript,
            "detected_language": detected_lang,
            "engine": engine
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

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

@router.post("/rta-sync")
def rta_sync_announcement(req: RTASyncRequest):
    """
    Direct sync endpoint for Real-Time Announcements (RTA) pulled from Station Announcer.
    Accepts incoming station announcement or sudden alert, runs Multilingual Translation,
    TTS synthesis, stores in SQLite, and returns translation matrix for the SETU client.

    OPTIMIZATION: If an identical transcript was already processed and cached,
    returns the existing cached result immediately — no duplicate translation/TTS work.
    """
    station_code = req.station_code.strip().upper()
    platform_number = (req.platform_number or "1").strip().upper()
    transcript = req.transcript.strip()
    source_language = req.source_language or "en"
    is_alert = bool(req.is_alert)
    alert_priority = req.alert_priority or ("CRITICAL" if is_alert else "NORMAL")

    tx_hash = _transcript_hash(transcript)

    # ── Dedup Guard: prevent concurrent processing of the exact same transcript ──
    if tx_hash in _processing_lock:
        logger.info(f"RTA sync SKIPPED (already being processed): '{transcript[:60]}…'")
        # Try to return cached result while the other request finishes
        existing = find_announcement_by_transcript(station_code, transcript)
        if existing:
            return {
                "status": "success",
                "message": f"Already cached (concurrent dedup) for {station_code}.",
                "announcement": existing,
                "from_cache": True
            }
        return {
            "status": "success",
            "message": f"Already being processed for {station_code}. Please retry shortly.",
            "announcement": {"cached_translations": []},
            "from_cache": True
        }

    # ── Cache Hit: check if this exact transcript was already translated ──
    existing = find_announcement_by_transcript(station_code, transcript)
    if existing and len(existing.get("cached_translations", [])) > 0:
        print("\n" + "="*70)
        print(f"⚡  [SETU RTA CACHE HIT — SKIPPING TRANSLATE/TTS]")
        print(f"   Station Code    : {station_code}")
        print(f"   Transcript      : \"{transcript[:80]}\"")
        print(f"   Cached langs    : {len(existing['cached_translations'])}")
        print("="*70 + "\n", flush=True)
        return {
            "status": "success",
            "message": f"Returned cached translations for {station_code} (no re-processing needed).",
            "announcement": existing,
            "from_cache": True
        }

    # ── Full processing pipeline ──
    _processing_lock.add(tx_hash)
    try:
        print("\n" + "="*70)
        print(f"📡  [SETU RTA SYNC - {'🚨 SUDDEN ALERT' if is_alert else 'ANNOUNCEMENT'}]")
        print(f"   Station Code    : {station_code}")
        print(f"   Platform Number : {platform_number}")
        print(f"   Priority        : {alert_priority}")
        print(f"   Transcript      : \"{transcript}\"")
        print("="*70 + "\n", flush=True)

        logger.info(f"Processing RTA sync: {station_code} P{platform_number} (Alert: {is_alert}): '{transcript}'")

        # 1. Save original announcement record in SQLite DB
        announcement = save_announcement(
            station_code=station_code,
            platform_number=platform_number,
            original_transcript=transcript,
            source_language=source_language,
            is_alert=is_alert,
            alert_priority=alert_priority
        )

        # 2. Translate into supported languages
        translations = translate_to_all_supported_languages(transcript, source_lang=source_language)
        if source_language not in translations:
            translations[source_language] = transcript

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
            "message": f"Processed RTA {'alert' if is_alert else 'announcement'} for {station_code}.",
            "announcement": {
                "id": announcement.id,
                "station_code": announcement.station_code,
                "platform_number": announcement.platform_number,
                "original_transcript": announcement.original_transcript,
                "source_language": announcement.source_language,
                "is_alert": is_alert,
                "alert_priority": alert_priority,
                "cached_translations": cached_results
            }
        }
    finally:
        _processing_lock.discard(tx_hash)

@router.get("/rta-poll")
def proxy_rta_poll(station_code: str = "NDLS", since_id: int = 0):
    """Proxy poll endpoint allowing SETU frontend to query port 8001 via port 8000 without CORS issues."""
    import urllib.request
    import json
    st = station_code.strip().upper()
    url = f"http://127.0.0.1:8001/api/station/{st}/poll?since_id={since_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SETU-Proxy/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.warning(f"RTA proxy poll failed connecting to port 8001: {e}")
        return {
            "status": "error",
            "message": f"Could not connect to Station Announcer at {url}: {str(e)}",
            "station_code": st,
            "has_updates": False,
            "new_announcements": [],
            "new_alerts": [],
            "active_alerts": []
        }

@router.get("/rta-feed")
def proxy_rta_feed(station_code: str = "NDLS"):
    """Proxy feed endpoint allowing SETU frontend to retrieve full station feed from port 8001."""
    import urllib.request
    import json
    st = station_code.strip().upper()
    url = f"http://127.0.0.1:8001/api/station/{st}/feed"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SETU-Proxy/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.warning(f"RTA proxy feed failed connecting to port 8001: {e}")
        return {
            "status": "error",
            "message": f"Could not connect to Station Announcer at {url}: {str(e)}",
            "station_code": st,
            "announcements": [],
            "active_alerts": []
        }


