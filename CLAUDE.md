# CLAUDE.md — Specialist Swarm

Project-level guide for Claude Code working in this repo. Read this before
making changes. It captures the architecture, conventions, and the agent team
that builds and reviews this project.

## What this repo is

A **coordinator + specialists + skills** multi-agent system built on Anthropic
[Managed Agents (multi-agent)](https://platform.claude.com/docs/en/managed-agents/multi-agent).
A coordinator agent delegates to specialist sub-agents — each with its own
narrow system prompt, its own custom [Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview),
and (where the work is rule-based rather than judgment-based) a deterministic
Python tool it calls via the bash tool — and synthesises their replies into a
single deliverable.

This repo currently builds **one scenario: Card D — Recruitment Drive**.
(An earlier Deal Desk scenario, Card A, was removed — its parallel-fan-out
pattern doesn't apply here and its files would only confuse this build.)

| Card | Coordinator | Specialists | Flow |
| --- | --- | --- | --- |
| **D — Recruitment Drive** (built) | Recruitment Drive Lead | Background Verification → JD Matching → Panelist Matching | **Sequential gated pipeline** — each stage gates the next, stop early on rejection |

The defining behavioural rule: the coordinator calls specialists **in order**,
one at a time, and must **stop early** the moment a gate fails (`REJECTED`
background check, or `REJECT` JD fit). Never have it fan out to all three at
once — that's the Deal Desk pattern, not this one. The system prompt enforces
this, and a backend (when built, see `backend.md`) must double-check the gates
server-side because a model could ignore the instruction.

## Design docs

- [`architecture.md`](./architecture.md) — Recruitment Drive Swarm: the gated
  pipeline, coordinator responsibilities, the three specialists + their skills
  and tools, data contracts.
- [`backend.md`](./backend.md) — FastAPI layer wrapping the swarm: resources,
  endpoints, the gated **drive status model**, how a drive executes, error
  handling. Storage is flat JSON under `data/` for demo scope. Not yet built.
- [`frontend.md`](./frontend.md) — React + Vite recruiter console: New Drive,
  live Drive Status (where *not progressing* is meaningful), Interview
  Readiness Pack, Panelist Pool. Not yet built.

## Repo layout

```
create_recruitment_specialists.py   # creates the 3 specialist sub-agents -> .recruitment_specialist_ids.json
create_recruitment_coordinator.py   # creates the coordinator (multiagent: coordinator) -> .recruitment_coordinator_id
upload_recruitment_skills.py        # packages skills/ via Skills API, attaches each to its specialist
setup_environment.py                # provisions the cloud Environment -> .environment_id
run_recruitment_drive.py            # runs the gated pipeline, streams events, downloads deliverables
download_deliverable.py             # pulls files from any past session, by session ID
skills/<name>/SKILL.md              # one custom skill per specialist domain
tools/verify_resume_dates.py        # deterministic employment-timeline check (background verification)
tools/match_panelists.py            # deterministic skill/availability/location matching (panel matching)
synthetic-data/                     # candidate-profile.{md,json}, sample_jd.md, panelist-pool.json
```

## Build & run order

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python setup_environment.py              # -> .environment_id
python create_recruitment_specialists.py # -> .recruitment_specialist_ids.json
python upload_recruitment_skills.py      # uploads + attaches skills
python create_recruitment_coordinator.py # -> .recruitment_coordinator_id
python run_recruitment_drive.py          # streams events, writes outputs/
```

The two tools under `tools/` are also runnable standalone for testing, e.g.
`python tools/match_panelists.py <input.json>` — see each script's docstring
for the expected input shape.

## Conventions (follow these exactly)

- **Beta header.** Agent-management calls use
  `default_headers={"anthropic-beta": "managed-agents-2026-04-01"}` on the
  `Anthropic` client. File listing/download passes
  `betas=["managed-agents-2026-04-01"]`.
- **Model selection per role.** The coordinator gets the most capable model
  (`claude-opus-4-7` — synthesis + gating judgment); domain specialists get
  `claude-sonnet-4-6`. State *why* in a comment when you pick.
- **Idempotent scripts.** Every create/upload script must be safe to re-run:
  reuse existing IDs from the dotfiles, detect already-uploaded skills by
  `display_title`, skip already-attached skills. Hackathon dev loops re-run
  constantly — never create duplicates.
- **State lives in dotfiles.** `.recruitment_specialist_ids.json`,
  `.recruitment_coordinator_id`, `.environment_id`, `.recruitment_skill_ids.json`,
  `.recruitment_last_session_id`. Don't invent a DB for demo scope; flat JSON
  under `data/` is the agreed storage for the backend when it's built.
- **Deterministic work goes in a tool, not a prompt.** Date-overlap math and
  skill/availability/location matching are rule-based — they live in
  `tools/*.py`, called by the specialist via the bash tool, not eyeballed by
  the model. Reserve the model for judgment calls (plausibility, narration,
  synthesis).
- **SKILL.md frontmatter.** Each skill bundle has a `SKILL.md` at its root with
  YAML frontmatter containing `name` and a trigger-rich `description` (state
  *when* to use the skill). Package with `files_from_dir`.
- **Specialist prompts are narrow.** A specialist owns one lane: list its
  inputs, the exact structured output it must return, and its severity/score
  vocabulary. No scope creep into other specialists' lanes.
- **The deliverable is the artifact, not chat.** The coordinator's synthesis
  is the Interview Readiness Pack — verdict, JD fit, panel slate with mode —
  not a vague summary. If a docx/branded skill is added later, the pack
  should render through it the same way Card A rendered to `.docx`.

## The agent team (`.claude/agents/`)

These Claude Code subagents build and review this project. The **Master
Orchestrator** owns decomposition and delegation; the **team leads** can spawn
their own sub-agents (they have the `Agent` tool) to parallelise their lane.

| Agent | Role |
| --- | --- |
| `master-orchestrator` | Decomposes a goal, delegates to the leads/specialists below, synthesises results |
| `requirements-gatherer` | Turns raw asks into a structured PRD: user stories, acceptance criteria, scope |
| `tech-arch` | System architecture, stack, module boundaries, data flow, trade-offs |
| `frontend-team-lead` | Owns the React/Vite console; spawns frontend sub-agents per screen/component |
| `backend-team-lead` | Owns the FastAPI layer + swarm scripts; spawns backend sub-agents per endpoint/module |
| `database-engineer` | Data contracts, JSON storage schema (and migration path to a real DB) |
| `testing-team-lead` | Test strategy; spawns QA sub-agents for unit/integration/e2e + bug tickets |
| `code-reviewer` | Reviews diffs for correctness, security, conventions before merge |
| `skill-creator` | Authors new `skills/<name>/SKILL.md` bundles following this repo's template |

When in doubt about model/effort per agent, follow the 3-tier rubric: trivial →
Haiku/low, single-subsystem → Sonnet/medium, cross-cutting design or synthesis →
Opus/high.
