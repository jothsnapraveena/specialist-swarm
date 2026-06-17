"""
Flat-JSON storage helpers for the Recruitment Drive backend. No database —
see backend.md: this is demo scope, and the schema below is deliberately
simple enough that a real DB migration later is mechanical.
"""

import json
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
CANDIDATES_DIR = DATA_DIR / "candidates"
JOBS_DIR = DATA_DIR / "jobs"
DRIVES_DIR = DATA_DIR / "drives"
PANELISTS_PATH = DATA_DIR / "panelists.json"

REPO_ROOT = Path(__file__).parent.parent
SEED_PANELIST_POOL = REPO_ROOT / "synthetic-data" / "panelist-pool.json"


def _ensure_dirs() -> None:
    for d in (CANDIDATES_DIR, JOBS_DIR, DRIVES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def save_candidate(text: str) -> str:
    _ensure_dirs()
    candidate_id = new_id("cand")
    write_json(CANDIDATES_DIR / f"{candidate_id}.json", {"id": candidate_id, "text": text})
    return candidate_id


def load_candidate(candidate_id: str) -> dict | None:
    return read_json(CANDIDATES_DIR / f"{candidate_id}.json")


def save_job(text: str) -> str:
    _ensure_dirs()
    job_id = new_id("job")
    write_json(JOBS_DIR / f"{job_id}.json", {"id": job_id, "text": text})
    return job_id


def load_job(job_id: str) -> dict | None:
    return read_json(JOBS_DIR / f"{job_id}.json")


def load_panelists() -> dict:
    _ensure_dirs()
    existing = read_json(PANELISTS_PATH)
    if existing is not None:
        return existing
    # Seed from the synthetic data used by the standalone swarm scripts so
    # GET /panelists returns something useful before anyone calls PUT.
    seed = read_json(SEED_PANELIST_POOL, {"interview_date": None, "panelist_pool": []})
    write_json(PANELISTS_PATH, seed)
    return seed


def save_panelists(data: dict) -> None:
    _ensure_dirs()
    write_json(PANELISTS_PATH, data)


def drive_dir(drive_id: str) -> Path:
    return DRIVES_DIR / drive_id


def save_drive_status(drive_id: str, status: dict) -> None:
    write_json(drive_dir(drive_id) / "status.json", status)


def load_drive_status(drive_id: str) -> dict | None:
    return read_json(drive_dir(drive_id) / "status.json")


def append_drive_event(drive_id: str, event: dict) -> None:
    events_path = drive_dir(drive_id) / "events.log"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def read_drive_events(drive_id: str, from_line: int = 0) -> list[dict]:
    events_path = drive_dir(drive_id) / "events.log"
    if not events_path.exists():
        return []
    lines = events_path.read_text().splitlines()[from_line:]
    return [json.loads(line) for line in lines if line.strip()]


def save_drive_report(drive_id: str, report: dict) -> None:
    write_json(drive_dir(drive_id) / "report.json", report)


def load_drive_report(drive_id: str) -> dict | None:
    return read_json(drive_dir(drive_id) / "report.json")
