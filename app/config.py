import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if available
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "SETU - Speech-Enabled Translation Utility"
    VERSION: str = "1.0.0"
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Google Cloud Text-to-Speech
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # Speech-to-Text Whisper Configuration
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")

    # Base URL for static file serving to Twilio / Web clients
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000").rstrip('/')

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    AUDIO_DIR: Path = STATIC_DIR / "audio"
    CACHE_DB_PATH: str = os.getenv("CACHE_DB_PATH", str(BASE_DIR / "setu_cache.db"))

    # Language Keypad Mappings (DTMF -> Language Code & Display Name)
    LANGUAGE_KEYPAD_MAP = {
        "1": {"code": "hi", "name": "Hindi", "bengali": "हिन्दी"},
        "2": {"code": "ta", "name": "Tamil", "bengali": "தமிழ்"},
        "3": {"code": "te", "name": "Telugu", "bengali": "తెలుగు"},
        "4": {"code": "kn", "name": "Kannada", "bengali": "கன்னட"},
        "5": {"code": "mr", "name": "Marathi", "bengali": "मराठी"},
        "6": {"code": "bn", "name": "Bengali", "bengali": "বাংলা"},
        "7": {"code": "gu", "name": "Gujarati", "bengali": "ગુજરાતી"},
        "8": {"code": "ml", "name": "Malayalam", "bengali": "മലയാളം"},
        "9": {"code": "pa", "name": "Punjabi", "bengali": "ਪੰਜਾਬੀ"}
    }

    # Supported language list
    SUPPORTED_LANGUAGES = {
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "mr": "Marathi",
        "bn": "Bengali",
        "gu": "Gujarati",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "or": "Odia",
        "en": "English"
    }

settings = Settings()

# Ensure directories exist
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
