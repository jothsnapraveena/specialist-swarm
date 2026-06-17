"""
FastAPI backend for the Recruitment Drive swarm. See backend.md for the full
design. Hackathon scope: no auth, no real DB (flat JSON under backend/data/),
no rate limiting.

Run from the repo root:
    uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend import storage
from backend.models import CandidateCreate, DriveCreate, JobCreate, PanelistPoolUpdate
from backend.swarm_runner import run_drive

load_dotenv(Path(__file__).parent.parent / ".env")

TERMINAL_STATUSES = {"REJECTED_BACKGROUND", "REJECTED_FIT", "COMPLETED", "FAILED"}

app = FastAPI(title="Recruitment Drive API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "recruitment-drive-api"}


@app.post("/candidates")
def create_candidate(body: CandidateCreate) -> dict:
    if not body.text.strip():
        raise HTTPException(400, "Candidate text must not be empty.")
    candidate_id = storage.save_candidate(body.text)
    return {"candidate_id": candidate_id}


@app.post("/jobs")
def create_job(body: JobCreate) -> dict:
    if not body.text.strip():
        raise HTTPException(400, "Job description text must not be empty.")
    job_id = storage.save_job(body.text)
    return {"job_id": job_id}


@app.get("/panelists")
def get_panelists() -> dict:
    return storage.load_panelists()


@app.put("/panelists")
def put_panelists(body: PanelistPoolUpdate) -> dict:
    data = body.model_dump()
    storage.save_panelists(data)
    return data


@app.post("/drives")
def create_drive(body: DriveCreate, background_tasks: BackgroundTasks) -> dict:
    candidate = storage.load_candidate(body.candidate_id)
    if candidate is None:
        raise HTTPException(404, f"candidate_id {body.candidate_id} not found.")
    job = storage.load_job(body.job_id)
    if job is None:
        raise HTTPException(404, f"job_id {body.job_id} not found.")

    drive_id = storage.new_id("drv")
    status_doc = {
        "drive_id": drive_id,
        "candidate_id": body.candidate_id,
        "job_id": body.job_id,
        "status": "PENDING",
        "background_check": None,
        "jd_match": None,
        "panel_match": None,
        "error": None,
    }
    storage.save_drive_status(drive_id, status_doc)
    background_tasks.add_task(run_drive, drive_id)
    return status_doc


@app.get("/drives/{drive_id}")
def get_drive(drive_id: str) -> dict:
    status_doc = storage.load_drive_status(drive_id)
    if status_doc is None:
        raise HTTPException(404, f"drive {drive_id} not found.")
    return status_doc


@app.get("/drives/{drive_id}/report")
def get_drive_report(drive_id: str) -> dict:
    report = storage.load_drive_report(drive_id)
    if report is None:
        raise HTTPException(404, f"No report yet for drive {drive_id} — check /drives/{drive_id} for status.")
    return report


@app.get("/drives/{drive_id}/events")
async def stream_drive_events(drive_id: str):
    if storage.load_drive_status(drive_id) is None:
        raise HTTPException(404, f"drive {drive_id} not found.")

    async def event_source():
        cursor = 0
        while True:
            new_events = storage.read_drive_events(drive_id, from_line=cursor)
            cursor += len(new_events)
            for event in new_events:
                yield f"data: {json.dumps(event)}\n\n"

            status_doc = storage.load_drive_status(drive_id)
            if status_doc and status_doc["status"] in TERMINAL_STATUSES and not new_events:
                yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_source(), media_type="text/event-stream")
