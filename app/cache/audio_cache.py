import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

Base = declarative_base()

class AnnouncementRecord(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_code = Column(String(20), nullable=False, index=True)
    platform_number = Column(String(20), nullable=False, index=True)
    original_transcript = Column(Text, nullable=False)
    source_language = Column(String(10), default="en")
    is_alert = Column(Integer, default=0)
    alert_priority = Column(String(20), default="NORMAL")
    created_at = Column(DateTime, default=datetime.utcnow)

    cached_audios = relationship("CachedAudioRecord", back_populates="announcement", cascade="all, delete-orphan")

class CachedAudioRecord(Base):
    __tablename__ = "cached_audio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id"), nullable=False)
    station_code = Column(String(20), nullable=False, index=True)
    platform_number = Column(String(20), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, index=True)
    translated_text = Column(Text, nullable=False)
    audio_file_path = Column(String(255), nullable=False)
    synthesis_engine = Column(String(50), default="gTTS")
    created_at = Column(DateTime, default=datetime.utcnow)

    announcement = relationship("AnnouncementRecord", back_populates="cached_audios")

# Compound index for super-fast lookup by (station, platform, language)
Index("idx_station_platform_lang", CachedAudioRecord.station_code, CachedAudioRecord.platform_number, CachedAudioRecord.language_code)

# Create database engine
engine = create_engine(
    f"sqlite:///{settings.CACHE_DB_PATH}",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize SQLite database tables and apply lightweight migrations if needed."""
    Base.metadata.create_all(bind=engine)
    # Check if is_alert / alert_priority columns exist in existing table
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE announcements ADD COLUMN is_alert INTEGER DEFAULT 0"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE announcements ADD COLUMN alert_priority VARCHAR(20) DEFAULT 'NORMAL'"))
            conn.commit()
        except Exception:
            pass

def save_announcement(
    station_code: str,
    platform_number: str,
    original_transcript: str,
    source_language: str = "en",
    is_alert: bool = False,
    alert_priority: str = "NORMAL"
) -> AnnouncementRecord:
    """Create or update an announcement entry."""
    db = SessionLocal()
    try:
        # Standardize station and platform identifiers
        st_code = station_code.strip().upper()
        p_num = platform_number.strip().upper()

        announcement = AnnouncementRecord(
            station_code=st_code,
            platform_number=p_num,
            original_transcript=original_transcript,
            source_language=source_language,
            is_alert=1 if is_alert else 0,
            alert_priority=alert_priority.upper() if alert_priority else "NORMAL"
        )
        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        return announcement
    finally:
        db.close()

def save_cached_audio(
    announcement_id: int,
    station_code: str,
    platform_number: str,
    language_code: str,
    translated_text: str,
    audio_file_path: str,
    synthesis_engine: str = "gTTS"
) -> CachedAudioRecord:
    """Save synthesized translated audio entry into SQLite cache."""
    db = SessionLocal()
    try:
        st_code = station_code.strip().upper()
        p_num = platform_number.strip().upper()
        lang_code = language_code.strip().lower()

        # Remove existing cached entry for this station + platform + language if any
        existing = db.query(CachedAudioRecord).filter(
            CachedAudioRecord.station_code == st_code,
            CachedAudioRecord.platform_number == p_num,
            CachedAudioRecord.language_code == lang_code
        ).first()

        if existing:
            db.delete(existing)

        record = CachedAudioRecord(
            announcement_id=announcement_id,
            station_code=st_code,
            platform_number=p_num,
            language_code=lang_code,
            translated_text=translated_text,
            audio_file_path=audio_file_path,
            synthesis_engine=synthesis_engine
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()

def get_cached_audio(station_code: str, platform_number: str, language_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached audio metadata for a given station, platform, and language."""
    db = SessionLocal()
    try:
        st_code = station_code.strip().upper()
        p_num = platform_number.strip().upper()
        lang_code = language_code.strip().lower()

        record = db.query(CachedAudioRecord).filter(
            CachedAudioRecord.station_code == st_code,
            CachedAudioRecord.platform_number == p_num,
            CachedAudioRecord.language_code == lang_code
        ).order_by(CachedAudioRecord.created_at.desc()).first()

        if record:
            return {
                "id": record.id,
                "announcement_id": record.announcement_id,
                "station_code": record.station_code,
                "platform_number": record.platform_number,
                "language_code": record.language_code,
                "translated_text": record.translated_text,
                "audio_file_path": record.audio_file_path,
                "synthesis_engine": record.synthesis_engine,
                "created_at": record.created_at.isoformat()
            }
        return None
    finally:
        db.close()

def get_latest_announcement(station_code: Optional[str] = None, platform_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the latest announcement for a station/platform or overall latest."""
    db = SessionLocal()
    try:
        query = db.query(AnnouncementRecord)
        if station_code:
            query = query.filter(AnnouncementRecord.station_code == station_code.strip().upper())
        if platform_number:
            query = query.filter(AnnouncementRecord.platform_number == platform_number.strip().upper())
        
        announcement = query.order_by(AnnouncementRecord.created_at.desc()).first()
        if announcement:
            return {
                "id": announcement.id,
                "station_code": announcement.station_code,
                "platform_number": announcement.platform_number,
                "original_transcript": announcement.original_transcript,
                "source_language": announcement.source_language,
                "is_alert": bool(getattr(announcement, "is_alert", 0)),
                "alert_priority": getattr(announcement, "alert_priority", "NORMAL"),
                "created_at": announcement.created_at.isoformat()
            }
        return None
    finally:
        db.close()

def find_announcement_by_transcript(station_code: str, transcript: str) -> Optional[Dict[str, Any]]:
    """Find the most recent announcement with matching transcript text for a station.
    
    Returns the announcement dict with full cached_translations if found,
    enabling the RTA sync endpoint to skip duplicate translate/TTS work.
    """
    db = SessionLocal()
    try:
        st_code = station_code.strip().upper()
        normalized = transcript.strip()

        announcement = db.query(AnnouncementRecord).filter(
            AnnouncementRecord.station_code == st_code,
            AnnouncementRecord.original_transcript == normalized
        ).order_by(AnnouncementRecord.created_at.desc()).first()

        if not announcement:
            return None

        # Gather cached translations
        translations = []
        for cache in announcement.cached_audios:
            translations.append({
                "language_code": cache.language_code,
                "translated_text": cache.translated_text,
                "audio_file_path": cache.audio_file_path,
                "audio_url": f"http://localhost:8000/static/{cache.audio_file_path}",
                "synthesis_engine": cache.synthesis_engine,
                "created_at": cache.created_at.isoformat()
            })

        return {
            "id": announcement.id,
            "station_code": announcement.station_code,
            "platform_number": announcement.platform_number,
            "original_transcript": announcement.original_transcript,
            "source_language": announcement.source_language,
            "is_alert": bool(getattr(announcement, "is_alert", 0)),
            "alert_priority": getattr(announcement, "alert_priority", "NORMAL"),
            "created_at": announcement.created_at.isoformat(),
            "cached_translations": translations
        }
    finally:
        db.close()

def list_all_announcements() -> List[Dict[str, Any]]:
    """List all stored station announcements along with available cached translations."""
    db = SessionLocal()
    try:
        announcements = db.query(AnnouncementRecord).order_by(AnnouncementRecord.created_at.desc()).all()
        result = []
        for ann in announcements:
            translations = []
            for cache in ann.cached_audios:
                translations.append({
                    "language_code": cache.language_code,
                    "translated_text": cache.translated_text,
                    "audio_file_path": cache.audio_file_path,
                    "synthesis_engine": cache.synthesis_engine,
                    "created_at": cache.created_at.isoformat()
                })
            result.append({
                "id": ann.id,
                "station_code": ann.station_code,
                "platform_number": ann.platform_number,
                "original_transcript": ann.original_transcript,
                "source_language": ann.source_language,
                "is_alert": bool(getattr(ann, "is_alert", 0)),
                "alert_priority": getattr(ann, "alert_priority", "NORMAL"),
                "created_at": ann.created_at.isoformat(),
                "cached_translations": translations
            })
        return result
    finally:
        db.close()
