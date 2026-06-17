"""
Drives one Recruitment Drive session against the coordinator, updating the
drive's status file as each gate resolves. Mirrors run_recruitment_drive.py's
session/event-stream pattern, but writes to the backend's flat-JSON store
instead of stdout, and never lets a gate the model ignores leak into the
reported status — the status transitions below are computed here, in the
backend, not trusted blindly from the model's narration.

Status detection is text-pattern based (the specialists are instructed to
lead with `VERDICT: ...` / `RECOMMENDATION: ...` lines — see the skills).
This is a hackathon-scope heuristic, not a structured-output contract; if the
model deviates from the format, the drive still completes, it just won't get
fine-grained intermediate status updates.
"""

import os
import re
import traceback
from pathlib import Path

from anthropic import Anthropic

from backend import storage

REPO_ROOT = Path(__file__).parent.parent
COORDINATOR_ID_PATH = REPO_ROOT / ".recruitment_coordinator_id"
ENVIRONMENT_ID_PATH = REPO_ROOT / ".environment_id"

VERDICT_RE = re.compile(r"VERDICT:\s*(LEGITIMATE|REJECTED)", re.IGNORECASE)
RECOMMENDATION_RE = re.compile(r"RECOMMENDATION:\s*(PROCEED|HOLD|REJECT)", re.IGNORECASE)
PANEL_RE = re.compile(r"^PANEL:|NO PANELIST CLEARED BOTH CRITERIA", re.IGNORECASE | re.MULTILINE)


def _status_doc(drive_id: str, candidate_id: str, job_id: str) -> dict:
    existing = storage.load_drive_status(drive_id)
    if existing:
        return existing
    return {
        "drive_id": drive_id,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "status": "PENDING",
        "background_check": None,
        "jd_match": None,
        "panel_match": None,
        "error": None,
    }


def _fail(drive_id: str, doc: dict, message: str) -> None:
    doc["status"] = "FAILED"
    doc["error"] = message
    storage.save_drive_status(drive_id, doc)
    storage.append_drive_event(drive_id, {"type": "error", "message": message})


def _build_context(candidate_text: str, job_text: str, panelist_pool: dict) -> str:
    import json

    blocks = [
        f"=====  DOCUMENT: candidate-profile  =====\n{candidate_text}",
        f"=====  DOCUMENT: job-description  =====\n{job_text}",
        f"=====  DOCUMENT: panelist-pool.json  =====\n{json.dumps(panelist_pool, indent=2)}",
    ]
    return "\n\n".join(blocks)


def run_drive(drive_id: str) -> None:
    status = storage.load_drive_status(drive_id)
    if status is None:
        return  # drive record vanished; nothing to do
    candidate_id = status["candidate_id"]
    job_id = status["job_id"]
    doc = _status_doc(drive_id, candidate_id, job_id)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        _fail(drive_id, doc, "ANTHROPIC_API_KEY is not set. Set it in .env and restart the server.")
        return

    if not COORDINATOR_ID_PATH.exists() or not ENVIRONMENT_ID_PATH.exists():
        _fail(
            drive_id, doc,
            "Recruitment coordinator not provisioned yet. From the repo root, run: "
            "python setup_environment.py && python create_recruitment_specialists.py "
            "&& python upload_recruitment_skills.py && python create_recruitment_coordinator.py",
        )
        return

    candidate = storage.load_candidate(candidate_id)
    job = storage.load_job(job_id)
    if candidate is None or job is None:
        _fail(drive_id, doc, "candidate_id or job_id not found.")
        return

    panelist_pool = storage.load_panelists()

    try:
        client = Anthropic()
        coordinator_id = COORDINATOR_ID_PATH.read_text().strip()
        environment_id = ENVIRONMENT_ID_PATH.read_text().strip()

        doc["status"] = "RUNNING_BACKGROUND_CHECK"
        storage.save_drive_status(drive_id, doc)
        storage.append_drive_event(drive_id, {"type": "status", "status": doc["status"]})

        session = client.beta.sessions.create(
            agent=coordinator_id,
            environment_id=environment_id,
            title=f"Recruitment Drive — {drive_id}",
        )

        user_message = (
            "A candidate has applied. Run the standard Recruitment Drive "
            "process — sequential and gated, not parallel:\n"
            "1. Background Verification Specialist first. Stop if REJECTED.\n"
            "2. JD Matching Specialist next, only if legitimate. Stop if REJECT.\n"
            "3. Panelist Matching Specialist last, only if PROCEED or HOLD.\n"
            "4. Synthesise the Interview Readiness Pack.\n\n"
            f"{_build_context(candidate['text'], job['text'], panelist_pool)}"
        )

        terminal = False
        background_seen = False
        recommendation_seen = False
        final_text_parts: list[str] = []

        with client.beta.sessions.events.stream(session.id) as stream:
            client.beta.sessions.events.send(
                session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": user_message}]}],
            )
            for event in stream:
                t = event.type
                storage.append_drive_event(drive_id, {"type": t})

                if t == "agent.message":
                    for block in event.content:
                        if getattr(block, "type", None) != "text":
                            continue
                        text = block.text
                        final_text_parts.append(text)
                        storage.append_drive_event(drive_id, {"type": "text", "text": text})

                        if not background_seen:
                            m = VERDICT_RE.search(text)
                            if m:
                                background_seen = True
                                verdict = m.group(1).upper()
                                doc["background_check"] = {"verdict": verdict, "raw": text}
                                if verdict == "REJECTED":
                                    doc["status"] = "REJECTED_BACKGROUND"
                                    terminal = True
                                else:
                                    doc["status"] = "RUNNING_JD_MATCH"
                                storage.save_drive_status(drive_id, doc)

                        if not terminal and background_seen and not recommendation_seen:
                            m = RECOMMENDATION_RE.search(text)
                            if m:
                                recommendation_seen = True
                                rec = m.group(1).upper()
                                doc["jd_match"] = {"recommendation": rec, "raw": text}
                                if rec == "REJECT":
                                    doc["status"] = "REJECTED_FIT"
                                    terminal = True
                                else:
                                    # PROCEED or HOLD both continue to panel matching —
                                    # see backend.md's note on why HOLD isn't terminal.
                                    doc["status"] = "RUNNING_PANEL_MATCH"
                                storage.save_drive_status(drive_id, doc)

                        if not terminal and recommendation_seen and doc.get("panel_match") is None:
                            if PANEL_RE.search(text):
                                doc["panel_match"] = {"raw": text}
                                storage.save_drive_status(drive_id, doc)

                elif t == "session.status_idle":
                    break

        if not terminal:
            doc["status"] = "COMPLETED"
        storage.save_drive_status(drive_id, doc)

        report = {
            "drive_id": drive_id,
            "status": doc["status"],
            "background_check": doc.get("background_check"),
            "jd_match": doc.get("jd_match"),
            "panel_match": doc.get("panel_match"),
            "full_transcript": "".join(final_text_parts),
        }
        storage.save_drive_report(drive_id, report)
        storage.append_drive_event(drive_id, {"type": "done", "status": doc["status"]})

    except Exception as exc:  # noqa: BLE001 — must never crash the server process
        _fail(drive_id, doc, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")
