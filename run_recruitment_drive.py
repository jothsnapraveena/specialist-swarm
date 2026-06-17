"""
Run the Recruitment Drive swarm against the synthetic candidate + JD +
panelist pool.

Inlines the inputs into the user message (same simplification Card A makes).
Streams events as they come in — here the interesting signal isn't
parallelism (there is none, by design) but the sequential gate-by-gate
progress: background check -> JD match -> panel match, stopping early on a
rejection.

Usage:
    python run_recruitment_drive.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


CANDIDATE_PATH = Path("synthetic-data/candidate-profile.md")
CANDIDATE_JSON_PATH = Path("synthetic-data/candidate-profile.json")
JD_PATH = Path("synthetic-data/sample_jd.md")
PANELIST_POOL_PATH = Path("synthetic-data/panelist-pool.json")
OUTPUT_DIR = Path("outputs")


def load_inputs_as_context() -> str:
    blocks = []
    for path in [CANDIDATE_PATH, CANDIDATE_JSON_PATH, JD_PATH, PANELIST_POOL_PATH]:
        if not path.exists():
            print(f"  WARNING: {path} missing — skipping")
            continue
        print(f"  including {path.name}")
        blocks.append(f"=====  DOCUMENT: {path.name}  =====\n{path.read_text()}")
    return "\n\n".join(blocks)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    if not Path(".recruitment_coordinator_id").exists() or not Path(".environment_id").exists():
        raise SystemExit(
            "Missing .recruitment_coordinator_id or .environment_id. Run "
            "setup_environment.py, create_recruitment_specialists.py, "
            "upload_recruitment_skills.py, then create_recruitment_coordinator.py first."
        )

    coordinator_id = Path(".recruitment_coordinator_id").read_text().strip()
    environment_id = Path(".environment_id").read_text().strip()

    client = Anthropic()

    print("Loading candidate profile + JD + panelist pool...")
    context = load_inputs_as_context()

    print(f"\nStarting session against coordinator {coordinator_id}...")
    session = client.beta.sessions.create(
        agent=coordinator_id,
        environment_id=environment_id,
        title="Recruitment Drive — Priya Nair / Senior Backend Engineer",
    )
    Path(".recruitment_last_session_id").write_text(session.id)

    user_message = (
        "A candidate has applied. Please run the standard Recruitment Drive "
        "process — sequential and gated, not parallel:\n"
        "1. Background Verification Specialist first. Stop if REJECTED.\n"
        "2. JD Matching Specialist next, only if legitimate. Stop if REJECT.\n"
        "3. Panelist Matching Specialist last, only if PROCEED or HOLD.\n"
        "4. Synthesise the Interview Readiness Pack.\n\n"
        "The deterministic tools (tools/verify_resume_dates.py and "
        "tools/match_panelists.py) are available via the bash tool — "
        "specialists should run them rather than hand-computing dates or "
        "skill overlap. The panelist pool's interview_date field is the "
        "interview window to check availability against.\n\n"
        f"{context}"
    )

    print("\n=== EVENT STREAM (watch the gate-by-gate progress) ===\n")
    final_text_parts: list[str] = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )
        for event in stream:
            t = event.type
            if t == "session.thread_created":
                print(f"  [stage started]    {event.agent_name}", flush=True)
            elif t == "session.thread_status_running":
                name = getattr(event, "agent_name", "?")
                print(f"  [running]          {name}", flush=True)
            elif t == "agent.thread_message_received":
                print(f"  [verdict <-]       {event.from_agent_name}", flush=True)
            elif t == "agent.thread_message_sent":
                print(f"  [delegate ->]      {event.to_agent_name}", flush=True)
            elif t == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif t == "agent.tool_use":
                print(f"\n  [tool: {getattr(event, 'name', '?')}]", flush=True)
            elif t == "session.status_idle":
                print("\n\n[drive finished]")
                break

    OUTPUT_DIR.mkdir(exist_ok=True)
    transcript_path = OUTPUT_DIR / "recruitment-drive-transcript.txt"
    transcript_path.write_text("".join(final_text_parts))
    print(f"\nCoordinator transcript saved to {transcript_path}")

    print("\nDownloading deliverables from the session container...")
    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )
    file_count = 0
    for f in files.data:
        out_path = OUTPUT_DIR / f.filename
        print(f"  {f.filename}  ->  {out_path}")
        content = client.beta.files.download(f.id)
        content.write_to_file(str(out_path))
        file_count += 1

    if file_count == 0:
        print("  (no files found — agents may have produced text-only output)")
    else:
        print(f"\nDownloaded {file_count} file(s) to {OUTPUT_DIR}/")

    print("\nView the full session (including all sub-agent threads) at:")
    print(f"  https://platform.claude.com/sessions/{session.id}")


if __name__ == "__main__":
    main()
