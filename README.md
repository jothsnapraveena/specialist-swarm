# Recruitment Drive Swarm

**Concept:** Skills, tools & sub-agents
**Tech:** [Claude Managed Agents multi-agent](https://platform.claude.com/docs/en/managed-agents/multi-agent) + [custom Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) + deterministic Python tools
**Output:** An Interview Readiness Pack — background-check verdict, JD fit
score, and a recommended interview panel (in-person/online), produced by a
coordinator that calls three specialists in a strict, gated order.

## The pitch

This is **coordinator + specialists + skills**, but unlike a typical
parallel-fan-out swarm, this one is a **sequential gated pipeline**: every
stage can stop the whole drive. A rejected background check never reaches JD
matching. A rejected JD match never reaches panel matching. Where the work is
rule-based rather than judgmental — date-overlap checks, skill/availability/
location matching — a specialist calls a deterministic Python tool instead of
eyeballing JSON.

See [`architecture.md`](./architecture.md) for the full pipeline design,
[`backend.md`](./backend.md) for the (not yet built) API layer, and
[`frontend.md`](./frontend.md) for the (not yet built) recruiter console.

## Setup

You need a workspace API key on the Console (multi-agent is currently in
research preview — your workspace may need to be granted access).

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

## The pipeline

```
Background Verification  →  JD Matching  →  Panelist Matching
   (LEGITIMATE | REJECTED)    (PROCEED | HOLD | REJECT)   (ranked panel slate, or "no match")
```

1. **Background Verification Specialist** (skill: `resume-verification-checklist`,
   tool: `tools/verify_resume_dates.py`) — validates the resume is internally
   consistent before anything else runs.
2. **JD Matching Specialist** (skill: `jd-matching-rubric`) — scores the
   verified candidate against the job description, must-haves gate the
   recommendation.
3. **Panelist Matching Specialist** (skill: `panelist-matching-policy`, tool:
   `tools/match_panelists.py`) — ranks panelists by skill overlap first,
   filters by availability second, and assigns In-Person/Online per panelist
   by comparing candidate and panelist location.

## Build & run

```bash
python setup_environment.py              # -> .environment_id
python create_recruitment_specialists.py # -> .recruitment_specialist_ids.json
python upload_recruitment_skills.py       # uploads + attaches skills
python create_recruitment_coordinator.py  # -> .recruitment_coordinator_id
python run_recruitment_drive.py           # streams events, writes outputs/
```

`run_recruitment_drive.py` runs the swarm against the synthetic candidate in
`synthetic-data/candidate-profile.md` against `synthetic-data/sample_jd.md`,
using `synthetic-data/panelist-pool.json` for panel matching. It streams
events as the pipeline moves stage to stage — watch for it stopping early if
a gate fails, that's the point of this design, not a bug.

The two tools are also runnable standalone for testing:

```bash
python tools/verify_resume_dates.py <path-to-employment-history.json>
python tools/match_panelists.py <path-to-match-input.json>
```

See each script's docstring for the exact input shape.

## What's in this repo

```
README.md
architecture.md                     (the swarm design — read this first)
backend.md                          (API layer design, not yet built)
frontend.md                         (recruiter console design, not yet built)
requirements.txt
setup_environment.py                (provisions the cloud Environment)
create_recruitment_specialists.py   (creates the 3 specialist sub-agents)
create_recruitment_coordinator.py   (creates the coordinator)
upload_recruitment_skills.py        (uploads + attaches skills via the Skills API)
run_recruitment_drive.py            (runs the gated pipeline, streams events)
download_deliverable.py             (pulls files from any past session)
skills/
├── resume-verification-checklist/SKILL.md
├── jd-matching-rubric/SKILL.md
└── panelist-matching-policy/SKILL.md
tools/
├── verify_resume_dates.py          (deterministic employment-timeline check)
└── match_panelists.py              (deterministic skill/availability/location matching)
synthetic-data/
├── candidate-profile.md            (resume, human-readable)
├── candidate-profile.json          (structured fields for the tools)
├── sample_jd.md                    (job description)
└── panelist-pool.json              (panelist skills, location, availability)
```
