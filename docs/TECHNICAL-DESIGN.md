# Talent Cortex — Technical Design Document

---

## 1. Overview

Talent Cortex is a recruiter-facing AI-powered recruitment platform composed of a FastAPI backend and a React/Vite frontend that orchestrates a three-stage sequentially-gated AI swarm. Each recruitment drive passes a candidate through Background Verification, JD Matching, and Panelist Matching specialists in strict order, with each gate either halting the drive or passing the candidate forward. The coordinator agent (claude-opus-4-7) manages gate enforcement and synthesizes specialist outputs; three specialist agents (claude-sonnet-4-6) each execute a single focused domain skill.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                 Recruiter UI  (React / Vite)              │
│  POST /candidates  POST /jobs  POST /drives               │
│  GET  /drives/{id}  (poll every 2,500 ms)                 │
│  GET  /drives/{id}/report  (json | docx)                  │
│  [SSE  GET /drives/{id}/events — stretch goal]            │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
                         ▼
┌──────────────────────────────────────────────────────────┐
│                 FastAPI Backend  (Python, async)          │
│  • Route handlers                                         │
│  • Background task (asyncio)                              │
│  • Flat JSON storage  ◄──────────────────────────────────┼──► data/
└────────────────────────┬─────────────────────────────────┘    ├── candidates/{id}.json
                         │ background task                       ├── jobs/{id}.json
                         ▼                                       ├── drives/{id}/
┌──────────────────────────────────────────────────────────┐    │   ├── status.json
│       Recruitment Drive Lead  (coordinator)               │    │   └── report.json
│       Model: claude-opus-4-7  (Tier T3)                  │    ├── panelists.json
│                                                           │    ├── progress.json  ◄─ dashboard seam
│  Gate 1 ─────────────────────────────────────────────────┼──► └── agents.json    ◄─ dashboard seam
│  ▼                                                        │
│  Background Verification Specialist (claude-sonnet-4-6)   │
│  Skill: background-check-social-vetting                   │
│  LEGITIMATE → Gate 2  |  REJECTED → REJECTED_BACKGROUND  │
│                                                           │
│  Gate 2 ─────────────────────────────────────────────────┤
│  ▼                                                        │
│  JD Matching Specialist         (claude-sonnet-4-6)       │
│  Skill: jd-matching-rubric                                │
│  PROCEED → Gate 3  |  HOLD → HOLD_FIT  |  REJECT → ...   │
│                                                           │
│  Gate 3 ─────────────────────────────────────────────────┤
│  ▼                                                        │
│  Panelist Matching Specialist   (claude-sonnet-4-6)       │
│  Skill: panelist-matching-policy                          │
│  panel_slate → COMPLETED  (empty slate allowed)           │
└──────────────────────────────────────────────────────────┘
```

> Pipeline is **sequential and gated**. No stage runs in parallel. A failed gate terminates the drive immediately.

---

## 3. Component Breakdown

### 3.1 Frontend (React / Vite)

The frontend is a single-page application built with React and Vite. It communicates with the backend exclusively via plain `fetch` calls and an optional SSE stream (stretch goal).

**Four Screens**

| Screen | Purpose |
|---|---|
| **Candidate Entry** | Paste/upload resume text; POST /candidates; receive candidate_id |
| **Job Entry** | Paste job description text; POST /jobs; receive job_id |
| **Drive Dashboard** | Select candidate_id + job_id; POST /drives; display live status |
| **Report Viewer** | Render full report from GET /drives/{id}/report; offer DOCX download |

**Polling Behavior**

After posting a new drive, the frontend enters a polling loop:

```
setInterval(() => fetch(`/drives/${driveId}`), 2500)
```

The poll loop stops when the returned `status` is one of the terminal states: `REJECTED_BACKGROUND`, `REJECTED_FIT`, `HOLD_FIT`, `COMPLETED`, or `FAILED`.

**SSE Stretch Goal**

`GET /drives/{id}/events` is a Server-Sent Events stream emitting swarm events in real time. When the browser connects, polling is suspended. SSE is not required for the primary flow.

---

### 3.2 Backend (FastAPI)

**Endpoint Overview**

The FastAPI application exposes seven endpoints covering candidate ingestion, job ingestion, panelist management, drive lifecycle, and reporting. All request and response bodies are JSON except the DOCX binary download.

**Background Task Pattern**

`POST /drives` returns immediately with a `drive_id` after writing an initial `status.json` with `status: PENDING`. A FastAPI background task (`BackgroundTasks`) is enqueued and begins the swarm execution asynchronously. Each stage transition writes the updated `status.json` so the polling endpoint always reflects current state.

**Flat JSON Storage**

All persistent state is stored as JSON files under `data/`. There is no database. Each entity type occupies its own directory. Drive artifacts live under `data/drives/{drive_id}/` with separate files for the polling-optimized status and the full report. See Section 6 for full data model details.

---

### 3.3 Swarm Scripts

| Script | Role |
|---|---|
| `create_recruitment_specialists.py` | Creates the three specialist sub-agents via the Anthropic API, binding each to its skill |
| `create_recruitment_coordinator.py` | Creates the Recruitment Drive Lead coordinator agent, wiring in references to the three specialists |
| `upload_recruitment_skills.py` | Uploads all three SKILL.md files to the Anthropic skill registry |
| `run_recruitment_drive.py` | CLI entry point to trigger a drive outside the web UI; useful for testing |

---

### 3.4 Skills

Each skill lives under `skills/<name>/SKILL.md` and is uploaded to the Anthropic skill registry. The coordinator binds specialist agents to their respective skills at creation time.

| Skill | Directory | Invoked At | Purpose |
|---|---|---|---|
| `background-check-social-vetting` | `skills/background-check-social-vetting/` | Gate 1 | Resume internal consistency checks + social/public profile signals; emits LEGITIMATE or REJECTED verdict with FLAGS |
| `jd-matching-rubric` | `skills/jd-matching-rubric/` | Gate 2 | Scores candidate against must-have and nice-to-have criteria; emits PROCEED / HOLD / REJECT recommendation with numeric score |
| `panelist-matching-policy` | `skills/panelist-matching-policy/` | Gate 3 | Matches candidate's required skills to panelist pool by skill overlap then availability; emits panel_slate |

---

### 3.5 Dashboard & Tracker Integration Seam

Two JSON files under `data/` are written by the swarm at runtime and consumed by the live telemetry dashboard (Flight Deck, served on `:8765`).

**`data/progress.json`** — Drive progress tracker. Updated at every status transition. The dashboard reads this file to render a live progress indicator for the current or most recent drive.

**`data/agents.json`** — Agent LED panel feed. Updated when each specialist starts and finishes. Shape:

```json
[
  { "role": "coordinator",   "model": "claude-opus-4-7",   "status": "running|idle|done", "tokens": 0 },
  { "role": "background",    "model": "claude-sonnet-4-6", "status": "running|idle|done", "tokens": 0 },
  { "role": "jd_matching",   "model": "claude-sonnet-4-6", "status": "running|idle|done", "tokens": 0 },
  { "role": "panel_matching","model": "claude-sonnet-4-6", "status": "running|idle|done", "tokens": 0 }
]
```

The dashboard uses `agents.json` to light the agent LED panel with per-agent model, status, and cumulative token count.

---

## 4. Full API Contract

### 4.1 Endpoint Summary

| Method | Path | Description |
|---|---|---|
| POST | `/candidates` | Ingest candidate resume text; returns candidate_id |
| POST | `/jobs` | Ingest job description text; returns job_id |
| GET | `/panelists` | Retrieve full panelist pool |
| PUT | `/panelists` | Replace full panelist pool (not a patch) |
| POST | `/drives` | Start a recruitment drive for a candidate+job pair |
| GET | `/drives/{id}` | Poll drive status (used by frontend at 2.5 s interval) |
| GET | `/drives/{id}/report` | Retrieve full report (json or docx) |
| GET | `/drives/{id}/events` | SSE stream of swarm events (stretch goal) |

---

### 4.2 Detailed Request / Response

#### POST /candidates

**Request**
```json
{ "resume_text": "<string, required, non-empty>" }
```

**Response 200**
```json
{ "candidate_id": "a1b2c3d4-..." }
```

**Response 400** — blank or whitespace `resume_text`

---

#### POST /jobs

**Request**
```json
{ "jd_text": "<string, required, non-empty>" }
```

**Response 200**
```json
{ "job_id": "e5f6g7h8-..." }
```

**Response 400** — blank or whitespace `jd_text`

---

#### GET /panelists

**Response 200** — array (empty array is valid)
```json
[
  {
    "id": "p1",
    "name": "Alice Cheng",
    "skills": ["Python", "ML", "System Design"],
    "location": "Singapore",
    "availability": [
      { "date": "2025-02-10", "slots": ["09:00-10:00", "14:00-15:00"] }
    ]
  }
]
```

---

#### PUT /panelists

**Request** — same array shape as GET /panelists (full replacement; not a patch)

**Response 200** — stored pool (same shape as request)

---

#### POST /drives

**Request**
```json
{ "candidate_id": "<string>", "job_id": "<string>" }
```

**Response 200**
```json
{ "drive_id": "d9e0f1a2-..." }
```

Initial `status` written to `data/drives/{drive_id}/status.json` is `PENDING`. The background task starts immediately after the response is sent.

---

#### GET /drives/{id}

**Response 200** — polling shape (used by frontend)

```json
{
  "drive_id": "d9e0f1a2-...",
  "status": "COMPLETED",
  "background_check": {
    "verdict": "LEGITIMATE",
    "flags": [
      { "severity": "minor", "message": "Gap in employment 2020-Q3" }
    ]
  },
  "jd_match": {
    "score": 82,
    "recommendation": "PROCEED",
    "missing": []
  },
  "panel_match": {
    "panel_slate": [
      {
        "name": "Alice Cheng",
        "skill_overlap": "Python, ML",
        "availability_slot": "2025-02-10 09:00-10:00",
        "mode": "In-Person",
        "reason": "Strong skill overlap; location matched; earliest available slot"
      }
    ]
  },
  "error": null
}
```

**`status` Enum Values**

| Value | Terminal? |
|---|---|
| `PENDING` | No |
| `RUNNING_BACKGROUND_CHECK` | No |
| `RUNNING_JD_MATCH` | No |
| `RUNNING_PANEL_MATCH` | No |
| `REJECTED_BACKGROUND` | **Yes** |
| `REJECTED_FIT` | **Yes** |
| `HOLD_FIT` | **Yes** |
| `COMPLETED` | **Yes** |
| `FAILED` | **Yes** |

**Field nullability**

- `background_check` is `null` until Gate 1 completes.
- `jd_match` is `null` until Gate 2 completes.
- `panel_match` is `null` until Gate 3 completes.
- `error` is `null` unless `status` is `FAILED`.

---

#### GET /drives/{id}/report

**Query parameter:** `format` = `"json"` (default) or `"docx"`

**format=json** — superset of the polling shape; `jd_match` includes two additional arrays:

```json
{
  "jd_match": {
    "score": 82,
    "recommendation": "PROCEED",
    "missing": [],
    "must_have": [
      { "skill": "Python", "status": "met", "points": 14 },
      { "skill": "FastAPI", "status": "met", "points": 14 }
    ],
    "nice_to_have": [
      { "skill": "Kubernetes", "status": "missing", "points": 0 }
    ]
  }
}
```

> `must_have` and `nice_to_have` are present **only** in the `/report` endpoint, never in the polling endpoint.

**format=docx** — binary DOCX download.
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Generated via `python-docx` or equivalent.

---

#### GET /drives/{id}/events (stretch goal)

Server-Sent Events stream. Each event carries a JSON payload describing a swarm transition or specialist output chunk. The frontend suspends polling when this connection is active.

---

## 5. Drive Status State Machine

### 5.1 Legal Transitions

| From | To | Trigger |
|---|---|---|
| `PENDING` | `RUNNING_BACKGROUND_CHECK` | Background task begins |
| `RUNNING_BACKGROUND_CHECK` | `RUNNING_JD_MATCH` | Specialist verdict = LEGITIMATE |
| `RUNNING_BACKGROUND_CHECK` | `REJECTED_BACKGROUND` *(terminal)* | Specialist verdict = REJECTED |
| `RUNNING_BACKGROUND_CHECK` | `FAILED` *(terminal)* | API error during Gate 1 |
| `RUNNING_JD_MATCH` | `RUNNING_PANEL_MATCH` | Specialist recommendation = PROCEED |
| `RUNNING_JD_MATCH` | `HOLD_FIT` *(terminal)* | Specialist recommendation = HOLD |
| `RUNNING_JD_MATCH` | `REJECTED_FIT` *(terminal)* | Specialist recommendation = REJECT |
| `RUNNING_JD_MATCH` | `FAILED` *(terminal)* | API error during Gate 2 |
| `RUNNING_PANEL_MATCH` | `COMPLETED` *(terminal)* | Specialist returns panel_slate (may be empty) |
| `RUNNING_PANEL_MATCH` | `FAILED` *(terminal)* | API error during Gate 3 |

Terminal states: `REJECTED_BACKGROUND`, `REJECTED_FIT`, `HOLD_FIT`, `COMPLETED`, `FAILED`

### 5.2 ASCII Flow

```
POST /drives
    │
    ▼
 PENDING
    │
    ▼
 RUNNING_BACKGROUND_CHECK
    │
    ├─ REJECTED ──────────────────► REJECTED_BACKGROUND  (terminal)
    │
    ├─ API error ─────────────────► FAILED  (terminal)
    │
    └─ LEGITIMATE
            │
            ▼
      RUNNING_JD_MATCH
            │
            ├─ REJECT ────────────► REJECTED_FIT  (terminal)
            │
            ├─ HOLD ──────────────► HOLD_FIT  (terminal)
            │
            ├─ API error ─────────► FAILED  (terminal)
            │
            └─ PROCEED
                    │
                    ▼
             RUNNING_PANEL_MATCH
                    │
                    ├─ API error ──► FAILED  (terminal)
                    │
                    └─ success ────► COMPLETED  (terminal)
```

---

## 6. Data Model & Storage

All state is stored as flat JSON files under `data/`. No database is used. File paths are deterministic from entity IDs.

### 6.1 File Map

| File | Written By | Read By |
|---|---|---|
| `data/candidates/{id}.json` | POST /candidates handler | Coordinator at drive start |
| `data/jobs/{id}.json` | POST /jobs handler | Coordinator at drive start |
| `data/panelists.json` | PUT /panelists handler | Panelist Matching Specialist |
| `data/drives/{id}/status.json` | Background task at each transition | GET /drives/{id} |
| `data/drives/{id}/report.json` | Background task at COMPLETED | GET /drives/{id}/report |
| `data/progress.json` | Background task at each transition | Live telemetry dashboard |
| `data/agents.json` | Background task per specialist start/end | Live telemetry dashboard LED panel |

---

### 6.2 Schema Definitions

**`data/candidates/{id}.json`**
```json
{
  "candidate_id": "a1b2c3d4-...",
  "resume_text": "<full resume text>",
  "location": "Singapore"
}
```
`location` is parsed from `resume_text` at ingest time for panelist mode matching.

---

**`data/jobs/{id}.json`**
```json
{
  "job_id": "e5f6g7h8-...",
  "jd_text": "<full job description text>"
}
```

---

**`data/panelists.json`**
```json
[
  {
    "id": "p1",
    "name": "Alice Cheng",
    "skills": ["Python", "ML", "System Design"],
    "location": "Singapore",
    "availability": [
      { "date": "2025-02-10", "slots": ["09:00-10:00", "14:00-15:00"] }
    ]
  }
]
```

Full replacement on PUT — not patched. Panelist Matching Specialist reads this file via the deterministic tool `python tools/match_panelists.py`.

---

**`data/drives/{id}/status.json`** — polling-optimized; `jd_match` omits `must_have`/`nice_to_have`
```json
{
  "drive_id": "d9e0f1a2-...",
  "status": "COMPLETED",
  "background_check": { "verdict": "LEGITIMATE", "flags": [] },
  "jd_match": { "score": 82, "recommendation": "PROCEED", "missing": [] },
  "panel_match": { "panel_slate": [ { "name": "Alice Cheng", "skill_overlap": "Python, ML", "availability_slot": "2025-02-10 09:00-10:00", "mode": "In-Person", "reason": "..." } ] },
  "error": null
}
```

---

**`data/drives/{id}/report.json`** — superset of status.json; `jd_match` includes full rubric breakdown
```json
{
  "drive_id": "d9e0f1a2-...",
  "status": "COMPLETED",
  "background_check": { "verdict": "LEGITIMATE", "flags": [] },
  "jd_match": {
    "score": 82,
    "recommendation": "PROCEED",
    "missing": [],
    "must_have": [ { "skill": "Python", "status": "met", "points": 14 } ],
    "nice_to_have": [ { "skill": "Kubernetes", "status": "missing", "points": 0 } ]
  },
  "panel_match": { "panel_slate": [ { "name": "Alice Cheng", "skill_overlap": "Python, ML", "availability_slot": "2025-02-10 09:00-10:00", "mode": "In-Person", "reason": "..." } ] },
  "error": null
}
```

---

**`data/progress.json`** — dashboard seam; written at every status transition
```json
{
  "drive_id": "d9e0f1a2-...",
  "status": "RUNNING_JD_MATCH",
  "stages_completed": ["background_check"],
  "current_stage": "jd_match",
  "started_at": "2025-02-10T08:00:00Z",
  "updated_at": "2025-02-10T08:00:45Z"
}
```

---

**`data/agents.json`** — dashboard agent LED panel seam; written when each specialist starts/finishes
```json
[
  { "role": "coordinator",    "model": "claude-opus-4-7",   "status": "done",    "tokens": 1240 },
  { "role": "background",     "model": "claude-sonnet-4-6", "status": "done",    "tokens": 870  },
  { "role": "jd_matching",    "model": "claude-sonnet-4-6", "status": "running", "tokens": 320  },
  { "role": "panel_matching", "model": "claude-sonnet-4-6", "status": "idle",    "tokens": 0    }
]
```

---

## 7. End-to-End Sequence

The following steps describe a complete drive execution from `POST /drives` to `COMPLETED`.

```
1.  Recruiter POSTs /candidates  →  candidate_id written to data/candidates/{id}.json
2.  Recruiter POSTs /jobs        →  job_id written to data/jobs/{id}.json
3.  Recruiter POSTs /drives      →  drive_id generated
                                     status.json written: { status: "PENDING" }
                                     progress.json written: { status: "PENDING" }
                                     FastAPI enqueues background task
                                     Response { drive_id } returned immediately
4.  Frontend begins polling GET /drives/{drive_id} every 2,500 ms

--- Background Task (async, runs concurrently with polling) ---

5.  Coordinator reads candidate + job files
6.  status.json updated → RUNNING_BACKGROUND_CHECK
    progress.json updated; agents.json: background = "running"

7.  Coordinator invokes Background Verification Specialist
    (Skill: background-check-social-vetting)
    Specialist runs Lane 1 (resume internal) and Lane 2 (social/public)
    Returns: VERDICT + FLAGS + SUMMARY

8.  ** Gate 1 enforcement — coordinator checks verdict **
    ** Server-side check also validates verdict field before proceeding **
    → REJECTED:   status.json → REJECTED_BACKGROUND (terminal); task ends
    → LEGITIMATE: continue

9.  status.json updated → RUNNING_JD_MATCH
    agents.json: background = "done", jd_matching = "running"

10. Coordinator invokes JD Matching Specialist
    (Skill: jd-matching-rubric)
    Specialist scores must-haves (70 pts) + nice-to-haves (30 pts)
    Returns: score + recommendation + missing + must_have[] + nice_to_have[] + REQUIRED_SKILLS_FOR_PANEL

11. ** Gate 2 enforcement — coordinator checks recommendation **
    ** Server-side check also validates recommendation field before proceeding **
    → REJECT: status.json → REJECTED_FIT (terminal); task ends
    → HOLD:   status.json → HOLD_FIT (terminal); task ends
    → PROCEED: continue

12. status.json updated → RUNNING_PANEL_MATCH
    agents.json: jd_matching = "done", panel_matching = "running"

13. Coordinator invokes Panelist Matching Specialist
    (Skill: panelist-matching-policy)
    Specialist calls deterministic tool: python tools/match_panelists.py <input-json>
    Tool filters by skill overlap first, then availability
    Returns: panel_slate (may be empty; never forces a weak match)

14. report.json written (full superset including must_have/nice_to_have)
    status.json updated → COMPLETED (terminal)
    progress.json updated; agents.json: panel_matching = "done"

15. Frontend poll receives status = "COMPLETED"; polling loop stops
16. Frontend fetches GET /drives/{id}/report to render full report
    Recruiter optionally downloads DOCX via GET /drives/{id}/report?format=docx
```

**Gate enforcement is doubly enforced:** the coordinator's system prompt instructs it never to invoke the next specialist on a gate failure, and the backend background task independently validates the gate output field before calling the coordinator's next step. Model instruction alone is not a sufficient guarantee; the server-side check is the authoritative gate.

---

## 8. Model Selection

| Role | Model | Tier | Why |
|---|---|---|---|
| Recruitment Drive Lead (coordinator) | `claude-opus-4-7` | T3 — Complex / Cross-cutting | Orchestrates a multi-step pipeline, enforces sequential gate logic, synthesizes outputs from three specialists, makes judgment calls across domains. Requires high reliability for gate decisions. |
| Background Verification Specialist | `claude-sonnet-4-6` | T2 — Moderate / Single-area | Single domain: evaluate resume + social signals. Structured output with well-defined verdict enum. Moderate logic; no cross-cutting reasoning needed. |
| JD Matching Specialist | `claude-sonnet-4-6` | T2 — Moderate / Single-area | Single domain: apply a fixed scoring rubric to a candidate against a JD. Deterministic scoring formula with defined thresholds. |
| Panelist Matching Specialist | `claude-sonnet-4-6` | T2 — Moderate / Single-area | Single domain: apply fixed decision order (skill → availability → mode). Calls a deterministic helper tool; structured output. |

**T2 vs T3 reasoning:**

T3 (Opus) is justified when the task requires synthesis across multiple information sources, judgment that affects downstream pipeline behavior, or orchestration of other agents. The coordinator meets all three criteria. T2 (Sonnet) is appropriate for single-domain tasks with well-scoped inputs, a defined output schema, and no need to reason about other agents' outputs. All three specialists meet these criteria.

---

## 9. Non-Functional Notes

### Demo Scope Exclusions

| Feature | Status | Reason |
|---|---|---|
| Authentication / authorization | Excluded | Demo scope; single recruiter |
| Multi-tenancy | Excluded | Single shared data/ directory |
| Real database | Excluded | Flat JSON is sufficient for demo |
| Rate limiting | Excluded | Single-user demo |
| Drive cancellation / pause | Excluded | Not in scope; drives run to completion |
| SSE streaming | Stretch goal | Polling is the primary mechanism |
| Horizontal scaling | Excluded | Single-process FastAPI; no shared-state handling |

### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Model ignores gate instruction and calls next specialist despite REJECTED verdict | Low but non-zero | **Server-side gate check** validates the verdict/recommendation field before the background task invokes the next stage. Model instruction alone is insufficient. |
| Flat JSON race condition (two concurrent drives writing same file) | Low in demo | Single-drive demo; no concurrent drive scenario. Accepted risk for demo scope. |
| Panelist pool empty or zero overlap | Expected | Specialist explicitly emits "NO PANELIST CLEARED BOTH CRITERIA"; empty `panel_slate` is a valid COMPLETED terminal state. |
| Model returns malformed JSON output | Possible | Coordinator and background task wrap specialist calls in try/except; malformed output transitions drive to FAILED with an error message. |
| DOCX generation failure (missing python-docx) | Possible | Backend returns 500 with a clear error; JSON report remains available. |
| Single must-have missing but score >= 70 | By design | JD Matching skill explicitly caps recommendation at HOLD in this case; coordinator and server-side check both enforce this. |
| candidate location not parseable from resume | Edge case | Panelist Matching Specialist falls back to Online mode for all panelists when location is ambiguous. |
