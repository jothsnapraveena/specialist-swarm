# CLAUDE.md — Specialist Swarm

Project-level guide for Claude Code working in this repo. Read this before
making changes. It captures the architecture, conventions, and the agent team
that builds and reviews this project.

## What this repo is

A **coordinator + specialists + skills** multi-agent system built on Anthropic
[Managed Agents (multi-agent)](https://platform.claude.com/docs/en/managed-agents/multi-agent).
A coordinator agent fans work out to 3–5 specialist sub-agents — each with its
own narrow system prompt and its own custom [Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) —
and synthesises their replies into a single branded deliverable (a `.docx`).

There are **two scenario cards** in this repo:

| Card | Coordinator | Specialists | Flow |
| --- | --- | --- | --- |
| **A — Deal Desk** (built) | Deal Desk Senior Partner | Pricing, Legal, Technical Fit, Competitive Intel (+ Critic stretch) | **Parallel** fan-out to all specialists at once |
| **D — Recruitment Drive** (designed, see `architecture.md`) | Recruitment Drive Lead | Background Verification → JD Matching → Panelist Matching | **Sequential gated pipeline** — each stage gates the next, stop early on rejection |

The single most important behavioural difference: Card A delegates to **all**
specialists in parallel; Card D calls specialists **in order** and must **stop
early** when a gate fails. Don't copy parallel fan-out into the recruitment
coordinator — its system prompt enforces sequential gating, and the backend
double-checks the gates because a model could ignore the instruction.

## Design docs (read these for the recruitment card)

- [`architecture.md`](./architecture.md) — Recruitment Drive Swarm: the gated
  pipeline, coordinator responsibilities, the three specialists + their skills,
  data contracts, and the file layout still to be built.
- [`backend.md`](./backend.md) — FastAPI layer wrapping the swarm: resources,
  endpoints, the gated **drive status model**, how a drive executes, error
  handling. Storage is flat JSON under `data/` for demo scope.
- [`frontend.md`](./frontend.md) — React + Vite recruiter console: New Drive,
  live Drive Status (where *not progressing* is meaningful), Interview
  Readiness Pack, Panelist Pool.
- [`scenario-cards.md`](./scenario-cards.md) — all the cards.
- [`stretch-goals.md`](./stretch-goals.md) — firm-voice skill, critic sub-agent,
  memory across deals, synthetic MCP.

## Repo layout

```
create_specialists.py        # creates the specialist sub-agents -> .specialist_ids.json
create_coordinator.py        # creates the coordinator (multiagent: coordinator) -> .coordinator_id
upload_skills.py             # packages skills/ via Skills API, attaches each to its specialist
setup_environment.py         # provisions the cloud Environment -> .environment_id
run_deal_desk.py             # runs the swarm against the RFP, streams events, downloads deliverables
download_deliverable.py      # pulls files from any past session
stretch_critic_subagent.py   # stretch: adds a Critic to the coordinator roster
skills/<name>/SKILL.md       # one custom skill per specialist domain
synthetic-data/              # RFP, past-wins, product-overview (Card A); candidate/JD/panelists (Card D)
```

## Build & run order (Card A)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python setup_environment.py        # -> .environment_id
python create_specialists.py       # -> .specialist_ids.json
python upload_skills.py            # uploads + attaches skills
python create_coordinator.py       # -> .coordinator_id
python run_deal_desk.py            # streams events, writes outputs/
```

The Recruitment Drive (Card D) mirrors this with
`create_recruitment_specialists.py`, `create_recruitment_coordinator.py`,
`upload_recruitment_skills.py`, `run_recruitment_drive.py` — additive, does not
touch the Deal Desk files.

## Conventions (follow these exactly)

- **Beta header.** Agent-management calls use
  `default_headers={"anthropic-beta": "managed-agents-2026-04-01"}` on the
  `Anthropic` client. File listing/download passes
  `betas=["managed-agents-2026-04-01"]`.
- **Model selection per role.** Coordinators and the Critic get the most
  capable model (`claude-opus-4-7`); domain specialists get `claude-sonnet-4-6`;
  cheap lookup specialists (e.g. Competitive Intel) get
  `claude-haiku-4-5-20251001`. State *why* in a comment when you pick.
- **Idempotent scripts.** Every create/upload script must be safe to re-run:
  reuse existing IDs from the dotfiles, detect already-uploaded skills by
  `display_title`, skip already-attached skills. Hackathon dev loops re-run
  constantly — never create duplicates.
- **State lives in dotfiles.** `.specialist_ids.json`, `.coordinator_id`,
  `.environment_id`, `.skill_ids.json`, `.last_session_id`. Don't invent a DB
  for demo scope; flat JSON under `data/` is the agreed storage.
- **SKILL.md frontmatter.** Each skill bundle has a `SKILL.md` at its root with
  YAML frontmatter containing `name` and a trigger-rich `description` (state
  *when* to use the skill). Package with `files_from_dir`.
- **Specialist prompts are narrow.** A specialist owns one lane: list its
  inputs, the exact structured output it must return, and its severity/score
  vocabulary. No scope creep into other specialists' lanes.
- **The deliverable is the artifact, not chat.** Coordinators produce a real
  `.docx` via the docx skill (or branded skill if available), downloaded from
  the session container — not a markdown message.

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
