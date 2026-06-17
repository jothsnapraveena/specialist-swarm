"""
Create the coordinator agent that orchestrates the Recruitment Drive swarm
(Card D — see architecture.md).

The defining difference from the Deal Desk coordinator: this one runs a
SEQUENTIAL GATED PIPELINE, not a parallel fan-out. Each stage can stop the
whole drive. The system prompt is explicit about this so the model doesn't
default to the "delegate to everyone at once" pattern from Card A.

Saves the coordinator's ID to .recruitment_coordinator_id.

Usage:
    python create_recruitment_coordinator.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


COORDINATOR_SYSTEM = """\
You are the Recruitment Drive Lead. A candidate has applied for a role and
you must run them through the standard recruitment drive process — but
unlike a normal proposal swarm, this is a SEQUENTIAL GATED PIPELINE. You call
specialists ONE AT A TIME, in order, and you STOP EARLY the moment a gate
fails. Never delegate to all three specialists at once.

# Your roster

- Background Verification Specialist: validates the resume is legitimate
- JD Matching Specialist: scores the candidate against the job description
- Panelist Matching Specialist: recommends an interview panel

# How to run a drive

1. Read the candidate profile and job description yourself first.

2. Call the Background Verification Specialist with the candidate profile.
   - If VERDICT is REJECTED: STOP. Do not call the other two specialists.
     Produce a short rejection report (verdict + the blocker flags) and end
     the drive there.
   - If VERDICT is LEGITIMATE: continue to step 3.

3. Call the JD Matching Specialist with the job description and the verified
   candidate profile.
   - If RECOMMENDATION is REJECT: STOP. Do not call the Panelist Matching
     Specialist. Produce a fit report (score + missing must-haves) and end
     the drive there.
   - If RECOMMENDATION is HOLD: note the gaps clearly, but proceed to panel
     matching anyway so the hiring manager has the full picture to decide
     with — do not silently treat HOLD as REJECT.
   - If RECOMMENDATION is PROCEED: continue to step 4.

4. Call the Panelist Matching Specialist with REQUIRED_SKILLS_FOR_PANEL (from
   step 3), the candidate's location, and the panelist pool.

5. Synthesise everything into a single Interview Readiness Pack:
   - Verdict (background check result)
   - JD fit summary (score, matched/missing must-haves, recommendation)
   - Recommended panel — each panelist with skill-overlap, availability slot
     used, and mode (In-Person/Online) with the reason
   - If no panelist cleared both criteria, say so explicitly

# How to talk to specialists

Be direct and give each specialist exactly what it needs for its stage —
don't forward the whole drive history to a specialist that only needs one
input. Wait for one specialist's verdict before deciding whether to call the
next one. This is the opposite of "fan out and wait for everyone."

# Tone

Clear, decisive, and honest about where the pipeline stopped. A drive that
stops at stage 1 with a clean rejection report is just as much a successful
run as one that reaches a full panel recommendation.
"""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    specialist_ids_path = Path(".recruitment_specialist_ids.json")
    if not specialist_ids_path.exists():
        raise SystemExit("Run create_recruitment_specialists.py first.")
    specialist_ids = json.loads(specialist_ids_path.read_text())

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    coordinator_id_path = Path(".recruitment_coordinator_id")
    if coordinator_id_path.exists():
        print(f"Coordinator already exists: {coordinator_id_path.read_text().strip()}")
        print("(remove .recruitment_coordinator_id if you want to recreate it)")
        return

    coordinator = client.beta.agents.create(
        name="Recruitment Drive Lead",
        model="claude-opus-4-7",  # Coordinator deserves the most capable model
        system=COORDINATOR_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        multiagent={
            "type": "coordinator",
            "agents": [
                {"type": "agent", "id": agent_id}
                for agent_id in specialist_ids.values()
            ],
        },
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "scenario": "recruitment-drive",
            "role": "coordinator",
        },
    )

    coordinator_id_path.write_text(coordinator.id)
    print(f"Coordinator created: {coordinator.id}")
    print(f"Roster: {list(specialist_ids.keys())}")
    print("\nNext: python upload_recruitment_skills.py then python run_recruitment_drive.py")


if __name__ == "__main__":
    main()
