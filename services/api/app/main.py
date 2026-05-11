from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI(
    title="ENIA Interaction Check API",
    version="0.1.0",
    description="Backend API for ENIA Interaction Check"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_rome():
    return datetime.now(ZoneInfo("Europe/Rome")).isoformat()

@app.get("/")
def root():
    return {
        "app": "ENIA Interaction Check",
        "status": "running",
        "checked_at": now_rome()
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "api",
        "checked_at": now_rome()
    }
