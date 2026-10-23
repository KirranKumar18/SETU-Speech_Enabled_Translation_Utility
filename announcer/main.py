import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = FastAPI(
    title="Station Announcer Console",
    version="1.0.0",
    description="Railway Station Master Announcement Dispatch Console & Alert Simulator"
)

# Enable CORS so SETU (running on port 8000) or other clients can freely query
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# In-memory storage for Station Announcements & Sudden Alerts
class StationStore:
    def __init__(self):
        self.next_id = 1
        self.stations: Dict[str, Dict[str, Any]] = {
            "NDLS": {
                "name": "New Delhi Railway Station",
                "code": "NDLS",
                "zone": "Northern Railway (NR)",
                "platforms": 16,
                "announcements": [],
                "alerts": []
            },
            "MAS": {
                "name": "Puratchi Thalaivar Dr. M.G. Ramachandran Central (Chennai Central)",
                "code": "MAS",
                "zone": "Southern Railway (SR)",
                "platforms": 12,
                "announcements": [],
                "alerts": []
            },
            "SBC": {
                "name": "KSR Bengaluru City Junction",
                "code": "SBC",
                "zone": "South Western Railway (SWR)",
                "platforms": 10,
                "announcements": [],
                "alerts": []
            },
            "CSMT": {
                "name": "Chhatrapati Shivaji Maharaj Terminus (Mumbai)",
                "code": "CSMT",
                "zone": "Central Railway (CR)",
                "platforms": 18,
                "announcements": [],
                "alerts": []
            }
        }
        self._seed_default_announcements()

    def _seed_default_announcements(self):
        ndls_seeds = [
            {
                "id": self._get_next_id(),
                "type": "regular",
                "station_code": "NDLS",
                "platform_number": "1",
                "train_number": "12951",
                "train_name": "Rajdhani Express",
                "transcript": "Attention passengers: Train number 12951 Rajdhani Express from New Delhi to Mumbai Central is arriving shortly on platform number 1.",
                "source_language": "en",
                "created_at": datetime.now().strftime("%H:%M:%S")
            },
            {
                "id": self._get_next_id(),
                "type": "regular",
                "station_code": "NDLS",
                "platform_number": "4",
                "train_number": "12004",
                "train_name": "Lucknow Shatabdi",
                "transcript": "May I have your attention please: Train number 12004 Lucknow Shatabdi Express is ready for departure from platform number 4.",
                "source_language": "en",
                "created_at": datetime.now().strftime("%H:%M:%S")
            }
        ]
        self.stations["NDLS"]["announcements"].extend(ndls_seeds)

    def _get_next_id(self) -> int:
        cur = self.next_id
        self.next_id += 1
        return cur

    def ensure_station(self, code: str):
        st = code.strip().upper()
        if st not in self.stations:
            self.stations[st] = {
                "name": f"Station {st}",
                "code": st,
                "zone": "Indian Railways",
                "platforms": 10,
                "announcements": [],
                "alerts": []
            }
        return self.stations[st]

store = StationStore()

# Pydantic Request Models
class AnnouncementCreate(BaseModel):
    transcript: str
    platform_number: str = "1"
    train_number: Optional[str] = None
    train_name: Optional[str] = None
    source_language: str = "en"

class SuddenAlertCreate(BaseModel):
    transcript: str
    platform_number: Optional[str] = "All"
    alert_type: str = "platform_change"  # 'platform_change', 'emergency', 'delay', 'security'
    priority: str = "CRITICAL"            # 'CRITICAL', 'WARNING', 'INFO'
    source_language: str = "en"

# Routes
@app.get("/api/stations")
def get_stations():
    """List all configured station hubs."""
    return [
        {
            "code": code,
            "name": data["name"],
            "zone": data["zone"],
            "platforms": data["platforms"],
            "announcements_count": len(data["announcements"]),
            "active_alerts_count": len(data["alerts"])
        }
        for code, data in store.stations.items()
    ]

@app.get("/api/station/{station_code}/feed")
def get_station_feed(station_code: str):
    """Retrieve all announcements and active sudden alerts for a station."""
    st = store.ensure_station(station_code)
    return {
        "status": "success",
        "station_code": st["code"],
        "station_name": st["name"],
        "zone": st["zone"],
        "announcements": list(reversed(st["announcements"])),
        "active_alerts": list(reversed(st["alerts"]))
    }

@app.get("/api/station/{station_code}/latest")
def get_latest(station_code: str):
    """Retrieve the most recent announcement and most recent active alert."""
    st = store.ensure_station(station_code)
    latest_ann = st["announcements"][-1] if st["announcements"] else None
    latest_alert = st["alerts"][-1] if st["alerts"] else None
    return {
        "status": "success",
        "station_code": st["code"],
        "latest_announcement": latest_ann,
        "latest_alert": latest_alert
    }

@app.get("/api/station/{station_code}/poll")
def poll_station(
    station_code: str,
    since_id: int = Query(0, description="Highest ID already seen by SETU")
):
    """
    Polling endpoint specifically for SETU to fetch all newly added announcements
    and sudden alerts since a given ID.
    """
    st = store.ensure_station(station_code)
    new_announcements = [a for a in st["announcements"] if a["id"] > since_id]
    new_alerts = [a for a in st["alerts"] if a["id"] > since_id]

    max_id = since_id
    if new_announcements:
        max_id = max(max_id, max(a["id"] for a in new_announcements))
    if new_alerts:
        max_id = max(max_id, max(a["id"] for a in new_alerts))

    return {
        "status": "success",
        "station_code": st["code"],
        "since_id": since_id,
        "latest_id": max_id,
        "has_updates": len(new_announcements) > 0 or len(new_alerts) > 0,
        "new_announcements": new_announcements,
        "new_alerts": new_alerts,
        "active_alerts": st["alerts"]
    }

@app.post("/api/station/{station_code}/announcements")
def create_announcement(station_code: str, req: AnnouncementCreate):
    """Announcer publishes a new station announcement."""
    st = store.ensure_station(station_code)
    item = {
        "id": store._get_next_id(),
        "type": "regular",
        "station_code": st["code"],
        "platform_number": req.platform_number.strip().upper(),
        "train_number": req.train_number.strip() if req.train_number else "",
        "train_name": req.train_name.strip() if req.train_name else "",
        "transcript": req.transcript.strip(),
        "source_language": req.source_language,
        "created_at": datetime.now().strftime("%H:%M:%S")
    }
    st["announcements"].append(item)
    return {
        "status": "success",
        "message": f"Announcement published successfully for {st['code']}.",
        "announcement": item
    }

@app.post("/api/station/{station_code}/alerts")
def create_sudden_alert(station_code: str, req: SuddenAlertCreate):
    """Announcer dispatches an urgent sudden alert."""
    st = store.ensure_station(station_code)
    item = {
        "id": store._get_next_id(),
        "type": "sudden_alert",
        "station_code": st["code"],
        "platform_number": req.platform_number.strip().upper() if req.platform_number else "ALL",
        "alert_type": req.alert_type,
        "priority": req.priority.upper(),
        "transcript": req.transcript.strip(),
        "source_language": req.source_language,
        "created_at": datetime.now().strftime("%H:%M:%S")
    }
    st["alerts"].append(item)
    return {
        "status": "success",
        "message": f"Sudden Alert broadcasted immediately for {st['code']}!",
        "alert": item
    }

@app.delete("/api/station/{station_code}/alerts/{alert_id}")
def dismiss_alert(station_code: str, alert_id: int):
    """Dismiss or resolve an active alert."""
    st = store.ensure_station(station_code)
    st["alerts"] = [a for a in st["alerts"] if a["id"] != alert_id]
    return {
        "status": "success",
        "message": f"Alert {alert_id} dismissed."
    }

# Mount static files and serve Announcer UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="announcer_static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Station Announcer Console API Running. index.html not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
