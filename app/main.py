import sys
import logging

# Ensure UTF-8 output encoding across Windows consoles to support Indic scripts and emojis
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.cache.audio_cache import init_db
from app.routes.announcements import router as announcements_router
from app.routes.ivr import router as ivr_router

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("setu.main")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-time IVR-based Multilingual Railway Station Announcement Translation Utility"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite database schema on startup
@app.on_event("startup")
def on_startup():
    logger.info("Initializing SQLite cache database tables...")
    init_db()
    logger.info("Database initialized successfully.")

# Register API routers
app.include_router(announcements_router)
app.include_router(ivr_router)

# Mount static folder for audio files & assets
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Serve Web Dashboard Index Page
@app.get("/")
async def serve_dashboard():
    index_file = settings.STATIC_DIR / "index.html"
    return FileResponse(str(index_file))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
