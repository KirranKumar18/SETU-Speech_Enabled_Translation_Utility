import logging
from typing import Optional
from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.cache.audio_cache import get_cached_audio, get_latest_announcement
from app.pipeline.translate import translate_text
from app.pipeline.synthesize import synthesize_speech
from app.config import settings

logger = logging.getLogger("setu.routes.ivr")

router = APIRouter(prefix="/api/ivr", tags=["ivr"])

@router.api_route("/incoming", methods=["GET", "POST"])
async def ivr_incoming(
    request: Request,
    station: Optional[str] = "NDLS",
    platform: Optional[str] = "1"
):
    """
    Initial Twilio Voice Webhook when passenger calls.
    Plays welcome message and requests language selection via DTMF keypad gather.
    """
    response = VoiceResponse()

    # Create Gather construct for single digit keypad input
    action_url = f"/api/ivr/handle-keypad?station={station}&platform={platform}"
    gather = Gather(numDigits=1, action=action_url, method="POST", timeout=8)

    gather.say(
        "Welcome to SETU Railway Announcement Utility. Please select your language. "
        "For Hindi press 1. "
        "For Tamil press 2. "
        "For Telugu press 3. "
        "For Kannada press 4. "
        "For Marathi press 5. "
        "For Bengali press 6. "
        "For Gujarati press 7. "
        "For Malayalam press 8. "
        "For Punjabi press 9.",
        voice="Polly.Aditi",
        language="en-IN"
    )

    response.append(gather)
    # If no digit entered
    response.say("We did not receive any keypad input. Goodbye!", voice="Polly.Aditi", language="en-IN")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")


@router.api_route("/handle-keypad", methods=["GET", "POST"])
async def ivr_handle_keypad(
    request: Request,
    Digits: Optional[str] = Form(None),
    station: Optional[str] = "NDLS",
    platform: Optional[str] = "1"
):
    """
    Handles keypad DTMF digit selection, retrieves cached audio, and plays audio to caller.
    """
    # Extract digit from Form data or Query parameters
    pressed_digit = Digits
    if not pressed_digit:
        form_data = await request.form()
        pressed_digit = form_data.get("Digits") or request.query_params.get("Digits")

    response = VoiceResponse()

    lang_info = settings.LANGUAGE_KEYPAD_MAP.get(str(pressed_digit))
    if not lang_info:
        # Invalid keypad selection
        gather = Gather(
            numDigits=1,
            action=f"/api/ivr/handle-keypad?station={station}&platform={platform}",
            method="POST"
        )
        gather.say("Invalid choice. Please press 1 for Hindi, 2 for Tamil, 3 for Telugu, or 4 for Kannada.", voice="Polly.Aditi", language="en-IN")
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

    lang_code = lang_info["code"]
    lang_name = lang_info["name"]

    st_code = station.strip().upper()
    p_num = platform.strip().upper()

    # Look up cached audio in SQLite
    cached = get_cached_audio(st_code, p_num, lang_code)

    if not cached:
        # Check if there is an existing announcement to synthesize on-the-fly
        announcement = get_latest_announcement(st_code, p_num) or get_latest_announcement()
        if announcement:
            transcript = announcement["original_transcript"]
            translated_text = translate_text(transcript, target_lang=lang_code)
            rel_path, _ = synthesize_speech(translated_text, st_code, p_num, lang_code)
            audio_url = f"{settings.BASE_URL}/static/{rel_path}"
        else:
            # Fallback default demo speech if DB has no announcements
            default_transcript = f"Attention passengers: Train 12951 Express to Mumbai Central is arriving on platform {p_num}."
            translated_text = translate_text(default_transcript, target_lang=lang_code)
            rel_path, _ = synthesize_speech(translated_text, st_code, p_num, lang_code)
            audio_url = f"{settings.BASE_URL}/static/{rel_path}"
    else:
        audio_url = f"{settings.BASE_URL}/static/{cached['audio_file_path']}"
        translated_text = cached["translated_text"]

    # Play translated announcement audio file to caller!
    response.say(f"Playing announcement in {lang_name}.", voice="Polly.Aditi", language="en-IN")
    response.play(audio_url)

    # Prompt user option to repeat or select another language
    gather_again = Gather(
        numDigits=1,
        action=f"/api/ivr/handle-keypad?station={st_code}&platform={p_num}",
        method="POST",
        timeout=5
    )
    gather_again.say("To hear this announcement in another language, press another key now.", voice="Polly.Aditi", language="en-IN")
    response.append(gather_again)

    response.say("Thank you for using SETU Railway Translation. Have a safe journey!", voice="Polly.Aditi", language="en-IN")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")


@router.post("/demo-call")
async def ivr_demo_simulator(
    digit: str = Form(...),
    station: str = Form("NDLS"),
    platform: str = Form("1")
):
    """
    In-browser IVR Call Simulator endpoint (JSON response for web app dialpad).
    """
    lang_info = settings.LANGUAGE_KEYPAD_MAP.get(str(digit))
    if not lang_info:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid keypad digit '{digit}'. Valid digits are 1-9."})

    lang_code = lang_info["code"]
    lang_name = lang_info["name"]

    cached = get_cached_audio(station, platform, lang_code)

    if not cached:
        # Fallback build announcement
        announcement = get_latest_announcement(station, platform) or get_latest_announcement()
        raw_text = announcement["original_transcript"] if announcement else f"Attention passengers: Train 12951 Express is arriving on platform {platform}."
        translated_text = translate_text(raw_text, target_lang=lang_code)
        rel_path, engine = synthesize_speech(translated_text, station, platform, lang_code)
        audio_url = f"{settings.BASE_URL}/static/{rel_path}"
    else:
        translated_text = cached["translated_text"]
        audio_url = f"{settings.BASE_URL}/static/{cached['audio_file_path']}"
        engine = cached.get("synthesis_engine", "Cached DB")

    return {
        "status": "success",
        "digit_pressed": digit,
        "language_code": lang_code,
        "language_name": lang_name,
        "station_code": station,
        "platform_number": platform,
        "translated_text": translated_text,
        "audio_url": audio_url,
        "synthesis_engine": engine
    }
