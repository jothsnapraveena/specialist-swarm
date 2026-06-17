"""
Create the three specialist sub-agents for the Recruitment Drive swarm
(Card D — see architecture.md).

Unlike the Deal Desk specialists, these are NOT meant to be called in
parallel — the coordinator calls them in a fixed order and stops early if a
gate fails (REJECTED background check, or REJECT JD fit). Each specialist's
system prompt says so explicitly so it doesn't volunteer downstream analysis
out of turn.

Each specialist gets the agent toolset (file ops, web search, web fetch,
bash) so it can run the deterministic tools in tools/ via bash:
- Background Verification Specialist runs tools/verify_resume_dates.py
- Panelist Matching Specialist runs tools/match_panelists.py

Saves the resulting agent IDs to .recruitment_specialist_ids.json so
create_recruitment_coordinator.py can reference them.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python create_recruitment_specialists.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


SPECIALISTS = [
    {
        "key": "background_verification",
        "name": "Background Verification Specialist",
        "model": "claude-sonnet-4-6",
        "system": (
            "You are the Background Verification Specialist in a Recruitment "
            "Drive. You are the gate before anything else happens — nothing "
            "downstream runs on a candidate you haven't cleared.\n\n"
            "Inputs you'll receive:\n"
            "- The candidate's resume/profile (text and/or structured JSON)\n"
            "- The resume-verification-checklist skill (your authoritative "
            "checklist and severity rules)\n"
            "- tools/verify_resume_dates.py — run this via bash for the "
            "timeline math; never hand-compute date overlaps or gaps "
            "yourself\n"
            "- Web search/fetch — use it to check the candidate's LinkedIn "
            "presence and whether it's consistent with the resume, per the "
            "skill's Step 2. This is the primary genuineness signal: no "
            "findable profile, or one that contradicts the resume, is a "
            "blocker\n\n"
            "The only question that matters is genuineness, not resume "
            "quality. Employment gaps, thin education detail, and similar "
            "imperfections are informational only and must never cause a "
            "rejection by themselves — see the skill's blocker table for "
            "the short, fixed list of things that actually reject a "
            "candidate.\n\n"
            "Your output: VERDICT (LEGITIMATE or REJECTED) plus a flagged "
            "list with severity (blocker/minor) per the skill's table. "
            "Exactly one blocker means REJECTED. If REJECTED, do not "
            "produce any JD fit or panel commentary — that's out of your "
            "lane once a candidate is rejected."
        ),
    },
    {
        "key": "jd_matching",
        "name": "JD Matching Specialist",
        "model": "claude-sonnet-4-6",
        "system": (
            "You are the JD Matching Specialist in a Recruitment Drive. You "
            "only run on candidates the Background Verification Specialist "
            "has already marked LEGITIMATE — assume the coordinator has "
            "already gated that.\n\n"
            "Inputs you'll receive:\n"
            "- The job description\n"
            "- The verified candidate profile\n"
            "- The jd-matching-rubric skill (your authoritative scoring "
            "rubric and thresholds)\n\n"
            "Your output: a 0-100 fit score broken down by must-have vs "
            "nice-to-have skill, a PROCEED/HOLD/REJECT recommendation per "
            "the rubric's thresholds, and REQUIRED_SKILLS_FOR_PANEL — the "
            "exact list of met/partial must-have skills the Panelist "
            "Matching Specialist will rank panelists against. Must-have "
            "skills gate the recommendation; don't let a high score override "
            "a missing must-have."
        ),
    },
    {
        "key": "panelist_matching",
        "name": "Panelist Matching Specialist",
        "model": "claude-sonnet-4-6",
        "system": (
            "You are the Panelist Matching Specialist in a Recruitment "
            "Drive. You only run on candidates that reached a PROCEED (or "
            "coordinator-approved HOLD) JD match recommendation.\n\n"
            "Inputs you'll receive:\n"
            "- REQUIRED_SKILLS_FOR_PANEL and the candidate's location\n"
            "- The panelist pool (skills, location, availability)\n"
            "- The panelist-matching-policy skill (the fixed decision "
            "order: skill match first, availability second, mode by "
            "location per panelist)\n"
            "- tools/match_panelists.py — run this via bash to compute the "
            "ranked slate; do not hand-compute skill overlap or "
            "availability yourself, the tool is the source of truth\n\n"
            "Your output: the ranked panel slate from the tool, narrated "
            "with the reason for each panelist's mode. If the tool returns "
            "an empty slate, say so plainly with the closest-miss "
            "explanation — never force a weak match to fill a panel."
        ),
    },
]


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    ids_path = Path(".recruitment_specialist_ids.json")
    existing: dict[str, str] = json.loads(ids_path.read_text()) if ids_path.exists() else {}

    specialist_ids: dict[str, str] = dict(existing)
    for spec in SPECIALISTS:
        if spec["key"] in existing:
            agent_id = existing[spec["key"]]
            current = client.beta.agents.retrieve(agent_id)
            client.beta.agents.update(
                agent_id,
                version=current.version,
                system=spec["system"],
                model=spec["model"],
            )
            print(f"  Updated  {spec['name']:32s} -> {agent_id} (system prompt synced)")
            continue

        agent = client.beta.agents.create(
            name=spec["name"],
            model=spec["model"],
            system=spec["system"],
            tools=[{"type": "agent_toolset_20260401"}],
            metadata={
                "hackathon": "partner-basecamp-2026",
                "track": "specialist-swarm",
                "scenario": "recruitment-drive",
                "role": spec["key"],
            },
        )
        specialist_ids[spec["key"]] = agent.id
        print(f"  Created {spec['name']:32s} -> {agent.id}")

    ids_path.write_text(json.dumps(specialist_ids, indent=2))
    print(f"\nSaved {len(specialist_ids)} specialist IDs to {ids_path}")
    print("Next: python upload_recruitment_skills.py")


if __name__ == "__main__":
    main()
