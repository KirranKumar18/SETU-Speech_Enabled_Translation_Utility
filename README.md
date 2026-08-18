# SETU - Speech-Enabled Translation Utility

SETU is a real-time IVR-based multilingual translation system for railway station announcements. Designed for hackathons and academic prototypes, SETU ensures that non-smartphone users and passengers unfamiliar with regional languages can dial a simple phone number, press a digit on their keypad, and instantly hear station announcements translated into their native language.

---

## 🚆 Problem SETU Solves
Railway PA system announcements are usually broadcast in the state language and English/Hindi. Many passengers—especially senior citizens, rural commuters, and feature-phone users without internet access—cannot understand local announcements or use apps like Google Translate.

SETU bridges this gap by enabling any passenger to dial a phone number, select their language via DTMF keypad input (`1` for Hindi, `2` for Tamil, `3` for Telugu, `4` for Kannada, etc.), and immediately listen to the station announcement translated into their spoken language.

---

## 🏗 Architecture (Record-Then-Serve)

```
 [ Station PA Announcement ] ──► (Upload / Mic Recording)
                                         │
                                         ▼
                               [ 1. Speech-to-Text ] (OpenAI Whisper)
                                         │
                                         ▼
                               [ 2. Translation ]    (IndicTrans2 / Indic Translator)
                                         │
                                         ▼
                               [ 3. Text-to-Speech ] (Google Cloud TTS / gTTS)
                                         │
                                         ▼
                               [ 4. SQLite Cache ]   (station, platform, lang -> mp3)
                                         │
                                         ▼
                               [ 5. Twilio IVR ]     (DTMF Keypad -> Audio Playback)
```

1. **Upload/Record**: Announcement audio is recorded or uploaded for a station (`station_code`) and platform (`platform_number`).
2. **Speech-to-Text (STT)**: Transcribed using OpenAI Whisper.
3. **Machine Translation**: Translated into regional Indian languages (Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Gujarati, Malayalam, Punjabi, Odia).
4. **Text-to-Speech (TTS)**: Synthesized into audio via Google Cloud TTS (or `gTTS` zero-setup fallback) and cached in SQLite.
5. **Telephony / IVR**: Passenger calls the Twilio phone number, inputs language choice via keypad, and listens to the cached announcement audio.

---

## 🚀 Quickstart Guide

### 1. Installation

```bash
# Navigate to project directory
cd setu

# Create virtual environment
python -m venv venv
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your credentials:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
BASE_URL=http://localhost:8000
```

> **Note**: If `GOOGLE_APPLICATION_CREDENTIALS` is omitted, SETU automatically uses `gTTS` as an offline fallback so you can demo the prototype immediately without active Google Cloud API keys!

### 3. Run FastAPI Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at `http://localhost:8000` to launch the **SETU Web Dashboard**.

---

## 📞 Twilio Voice Integration (Live Phone Calls)

1. Start `ngrok` tunnel to expose port 8000:
   ```bash
   ngrok http 8000
   ```
2. Copy your public ngrok URL (e.g., `https://a1b2c3.ngrok-free.app`).
3. Set `BASE_URL` in `.env` to your ngrok URL and restart `uvicorn`:
   ```env
   BASE_URL=https://a1b2c3.ngrok-free.app
   ```
4. In your **Twilio Console** -> Phone Numbers -> Active Numbers:
   - Under **Voice & Fax**, set **A CALL COMES IN** to **Webhook** (HTTP POST).
   - Set URL: `https://a1b2c3.ngrok-free.app/api/ivr/incoming`
5. Dial your Twilio phone number from any mobile or feature phone!

---

## 📁 Project Structure

```
setu/
├── app/
│   ├── main.py                 # FastAPI application entrypoint & static routes
│   ├── config.py               # Settings & language keypad mappings
│   ├── routes/
│   │   ├── announcements.py    # STT/Translation/TTS upload & cache API
│   │   └── ivr.py              # Twilio Voice TwiML webhook endpoints
│   ├── pipeline/
│   │   ├── transcribe.py       # OpenAI Whisper STT wrapper
│   │   ├── translate.py        # IndicTrans2 / Indic translation pipeline
│   │   └── synthesize.py       # Google Cloud TTS & gTTS fallback wrapper
│   └── cache/
│       └── audio_cache.py      # SQLite DB tables & cache functions
├── static/
│   ├── audio/                  # Cached synthesized mp3 audio files
│   └── index.html              # Interactive Web Dashboard & IVR Phone Simulator
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧪 Testing & Verification

1. **Web Dashboard**: Upload audio or type an announcement for `NDLS`, Platform `1`.
2. **Multilingual Matrix**: View side-by-side translated text and play audio streams for Hindi, Tamil, Telugu, Kannada, etc.
3. **In-Browser IVR Simulator**: Click **START IVR DEMO CALL** in the right-side phone panel and press keys 1-9 to simulate a live phone call directly in your browser.
