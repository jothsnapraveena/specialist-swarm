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

import logging
import os
import re
import traceback
from pathlib import Path

from anthropic import Anthropic

from backend import storage

logger = logging.getLogger("recruitment_drive")

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


def _scan_for_stage_markers(drive_id: str, text: str, source: str, doc: dict, flags: dict) -> None:
    """
    Looks for the skills' literal VERDICT:/RECOMMENDATION:/PANEL: markers in
    a text block and advances doc/flags accordingly. Called against BOTH the
    coordinator's own narration (agent.message) and the specialist's raw
    reply (agent.thread_message_received) — the specialist is the reliable
    source since it's instructed to use the literal format; the coordinator
    sometimes paraphrases its synthesis instead of echoing the marker.
    """
    if not flags["background_seen"]:
        m = VERDICT_RE.search(text)
        if m:
            flags["background_seen"] = True
            verdict = m.group(1).upper()
            doc["background_check"] = {"verdict": verdict, "raw": text}
            logger.info("[%s] BACKGROUND VERIFICATION verdict=%s (source=%s)", drive_id, verdict, source)
            if verdict == "REJECTED":
                doc["status"] = "REJECTED_BACKGROUND"
                flags["terminal"] = True
            else:
                doc["status"] = "RUNNING_JD_MATCH"
            storage.save_drive_status(drive_id, doc)

    if not flags["terminal"] and flags["background_seen"] and not flags["recommendation_seen"]:
        m = RECOMMENDATION_RE.search(text)
        if m:
            flags["recommendation_seen"] = True
            rec = m.group(1).upper()
            doc["jd_match"] = {"recommendation": rec, "raw": text}
            logger.info("[%s] JD MATCH recommendation=%s (source=%s)", drive_id, rec, source)
            if rec == "REJECT":
                doc["status"] = "REJECTED_FIT"
                flags["terminal"] = True
            else:
                # PROCEED or HOLD both continue to panel matching — see
                # backend.md's note on why HOLD isn't terminal.
                doc["status"] = "RUNNING_PANEL_MATCH"
            storage.save_drive_status(drive_id, doc)

    if not flags["terminal"] and flags["recommendation_seen"] and doc.get("panel_match") is None:
        if PANEL_RE.search(text):
            doc["panel_match"] = {"raw": text}
            logger.info("[%s] PANEL MATCH captured (source=%s)", drive_id, source)
            storage.save_drive_status(drive_id, doc)


def run_drive(drive_id: str) -> None:
    status = storage.load_drive_status(drive_id)
    if status is None:
        return  # drive record vanished; nothing to do
    candidate_id = status["candidate_id"]
    job_id = status["job_id"]
    doc = _status_doc(drive_id, candidate_id, job_id)

    logger.info("[%s] starting drive (candidate=%s, job=%s)", drive_id, candidate_id, job_id)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("[%s] ANTHROPIC_API_KEY not set — failing drive", drive_id)
        _fail(drive_id, doc, "ANTHROPIC_API_KEY is not set. Set it in .env and restart the server.")
        return

    if not COORDINATOR_ID_PATH.exists() or not ENVIRONMENT_ID_PATH.exists():
        logger.error("[%s] coordinator/environment not provisioned — failing drive", drive_id)
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
        logger.error("[%s] candidate_id or job_id not found", drive_id)
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
        logger.info("[%s] -> RUNNING_BACKGROUND_CHECK", drive_id)

        session = client.beta.sessions.create(
            agent=coordinator_id,
            environment_id=environment_id,
            title=f"Recruitment Drive — {drive_id}",
        )
        logger.info("[%s] session %s created against coordinator %s", drive_id, session.id, coordinator_id)

        user_message = (
            "A candidate has applied. Run the standard Recruitment Drive "
            "process — sequential and gated, not parallel:\n"
            "1. Background Verification Specialist first. Stop if REJECTED.\n"
            "2. JD Matching Specialist next, only if legitimate. Stop if REJECT.\n"
            "3. Panelist Matching Specialist last, only if PROCEED or HOLD.\n"
            "4. Synthesise the Interview Readiness Pack.\n\n"
            f"{_build_context(candidate['text'], job['text'], panelist_pool)}"
        )

        flags = {"terminal": False, "background_seen": False, "recommendation_seen": False}
        final_text_parts: list[str] = []

        with client.beta.sessions.events.stream(session.id) as stream:
            client.beta.sessions.events.send(
                session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": user_message}]}],
            )
            for event in stream:
                t = event.type
                storage.append_drive_event(drive_id, {"type": t})

                if t == "session.thread_created":
                    logger.info("[%s] specialist thread spawned: %s", drive_id, getattr(event, "agent_name", "?"))

                elif t == "agent.tool_use":
                    logger.info("[%s] tool call: %s", drive_id, getattr(event, "name", "?"))

                elif t == "agent.message":
                    # The coordinator's own narration/synthesis — always kept
                    # for the final transcript, and scanned as a fallback.
                    for block in event.content:
                        if getattr(block, "type", None) != "text":
                            continue
                        text = block.text
                        final_text_parts.append(text)
                        storage.append_drive_event(drive_id, {"type": "text", "text": text})
                        logger.info("[%s] coordinator: %s", drive_id, text[:160].replace("\n", " "))
                        _scan_for_stage_markers(drive_id, text, "coordinator", doc, flags)

                elif t == "agent.thread_message_received":
                    # The specialist's actual reply — this is the reliable
                    # source for the literal VERDICT:/RECOMMENDATION: markers,
                    # since the coordinator sometimes paraphrases instead.
                    from_agent = getattr(event, "from_agent_name", "?")
                    for block in event.content:
                        if getattr(block, "type", None) != "text":
                            continue
                        text = block.text
                        storage.append_drive_event(
                            drive_id, {"type": "specialist_reply", "from_agent_name": from_agent, "text": text}
                        )
                        logger.info("[%s] %s replied: %s", drive_id, from_agent, text[:200].replace("\n", " "))
                        _scan_for_stage_markers(drive_id, text, from_agent, doc, flags)

                elif t == "session.status_idle":
                    logger.info("[%s] session idle — drive finishing", drive_id)
                    break

        if not flags["terminal"]:
            doc["status"] = "COMPLETED"
        storage.save_drive_status(drive_id, doc)
        logger.info("[%s] DONE — final status %s", drive_id, doc["status"])

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
        logger.exception("[%s] drive failed", drive_id)
        _fail(drive_id, doc, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")
