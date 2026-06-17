# Requirements Specification — Recruitment Drive Swarm (Card D)

**Version:** 1.0  
**Date:** 2026-06-17  
**Author:** Requirements Gatherer agent  
**Status:** Draft — open questions listed in §7 require human decision before build

---

## 1. Goal

Build a recruiter-facing web application — the **Recruitment Drive Console** — that wraps a three-stage, sequentially-gated AI swarm (Background Verification → JD Matching → Panelist Matching) behind an HTTP API and a React UI. A recruiter pastes a candidate resume and a job description, submits a drive, watches the swarm progress stage-by-stage in near-real time, and receives a fully-reasoned **Interview Readiness Pack** recommending a panel of interviewers with skill-overlap rationale, availability slots, and interview mode (In-Person or Online) — all without touching the Anthropic console or reading raw JSON. The system is intentionally designed as a sequential pipeline where each stage acts as a gate: a failure at any gate stops the pipeline immediately and returns a targeted rejection report, avoiding wasteful LLM calls on already-disqualified candidates.

---

## 2. Scope

### 2.1 In Scope

1. FastAPI backend serving the seven endpoints defined in §5.
2. React + Vite frontend implementing four screens: New Drive, Drive Status, Interview Readiness Pack, Panelist Pool.
3. Sequential, gated swarm execution: Background Verification → JD Matching → Panelist Matching, with early-stop on gate failure.
4. Drive status polling (2.5 s interval) via `GET /drives/{id}`.
5. SSE event stream endpoint `GET /drives/{id}/events` (stretch — see §7).
6. Flat JSON file storage under `data/` (no database).
7. Panelist pool editable in bulk via UI (JSON textarea) and API (`PUT /panelists`).
8. Report export as JSON; DOCX export available via `GET /drives/{id}/report?format=docx`.
9. Synthetic data: `candidate-profile.md`, `sample_jd.md`, `panelist-pool.json`.
10. Python specialist/coordinator creation scripts mirroring Card A's pattern.

### 2.2 Out of Scope (deliberately omitted for demo)

1. **Authentication and authorisation** — no login, no API keys, no session tokens.
2. **Multi-tenancy** — a single shared panelist pool; no per-recruiter namespacing.
3. **Real database** — SQLite, Postgres, and any ORM are excluded; flat JSON files only.
4. **Rate limiting** — no request throttling on any endpoint.
5. **Cancel/pause a running drive** — cancel-and-resubmit is the supported workaround.
6. **Mobile responsiveness** — internal desk tool; desktop layout only.
7. **Multi-recruiter live views** — one in-flight drive per browser session.
8. **Document-forensic background checks** — textual consistency only, no actual database lookups.

---

## 3. User Stories

| # | Story |
|---|-------|
| US-01 | As a recruiter, I want to paste a candidate resume and a job description into a form and start a drive with one click, so that I do not need to touch any code or API client. |
| US-02 | As a recruiter, I want to watch each pipeline stage update in near-real time, so that I know the drive is progressing and where it stands at any moment. |
| US-03 | As a recruiter, I want the drive to stop immediately and show me specific rejection flags when background verification fails, so that I do not waste time waiting for JD or panel matching on a disqualified candidate. |
| US-04 | As a recruiter, I want to see the JD fit score and missing skills when a candidate does not meet the job requirements, so that I can decide whether to revisit the JD or the candidate. |
| US-05 | As a recruiter, I want the system to place a drive on hold when the JD match score is borderline, so that a human can decide whether to proceed rather than auto-rejecting. |
| US-06 | As a recruiter, I want to receive a recommended interview panel with skill-overlap percentage, the specific availability slot used, and the interview mode (In-Person or Online) with a plain-language reason, so that I can defend the panel choice to a hiring manager without reading raw output. |
| US-07 | As a recruiter, I want an explicit "no panelist cleared both criteria" message when the pool cannot satisfy the constraints, so that I know I need to update the pool rather than assume the panel will be arranged. |
| US-08 | As a recruiter, I want to download the Interview Readiness Pack as a DOCX file, so that I can share it with stakeholders via email or a document management system. |
| US-09 | As a recruiter, I want to view and bulk-edit the panelist pool from the UI, so that I can update availability or skills without touching any files or code. |
| US-10 | As a recruiter, I want to retry a failed drive (Anthropic API error) without re-entering the candidate or JD text, so that a transient error does not require me to start over. |

---

## 4. Acceptance Criteria

### US-01 — New Drive submission

**AC-01.1**
Given the New Drive form is open,  
When the recruiter submits with an empty resume field,  
Then the form shows the inline error "Resume text is required." and does NOT call any API endpoint.

**AC-01.2**
Given the New Drive form is open,  
When the recruiter submits with an empty JD field,  
Then the form shows the inline error "Job description is required." and does NOT call any API endpoint.

**AC-01.3**
Given valid resume text and JD text are entered,  
When the recruiter clicks "Start Recruitment Drive →",  
Then the frontend calls `POST /candidates` and `POST /jobs` in parallel, then calls `POST /drives` with the returned IDs, and navigates to the Drive Status screen with the returned `drive_id`.

**AC-01.4**
Given `POST /candidates` receives a blank or whitespace-only `resume_text`,  
When the backend validates the request,  
Then the backend returns HTTP 400 before creating any Anthropic session.

**AC-01.5**
Given `POST /jobs` receives a blank or whitespace-only `jd_text`,  
When the backend validates the request,  
Then the backend returns HTTP 400 before creating any Anthropic session.

---

### US-02 — Live drive status

**AC-02.1**
Given a drive has been created,  
When the Drive Status screen is open,  
Then the frontend polls `GET /drives/{id}` every 2,500 ms until the status is terminal.

**AC-02.2**
Given the drive status is non-terminal,  
When the Drive Status screen renders,  
Then a pulsing indicator is visible and the polling continues.

**AC-02.3**
Given the drive status becomes terminal,  
When the frontend receives the terminal status,  
Then polling stops and no further requests are made to `GET /drives/{id}`.

**AC-02.4**
Given status is `PENDING`,  
When the Stage rows render,  
Then Background Verification shows "pending", JD Match shows "pending", Panelist Matching shows "pending".

**AC-02.5**
Given status is `RUNNING_BACKGROUND_CHECK`,  
When the Stage rows render,  
Then Background Verification shows "running", JD Match shows "pending", Panelist Matching shows "pending".

**AC-02.6**
Given status is `RUNNING_JD_MATCH`,  
When the Stage rows render,  
Then Background Verification shows "passed", JD Match shows "running", Panelist Matching shows "pending".

**AC-02.7**
Given status is `RUNNING_PANEL_MATCH`,  
When the Stage rows render,  
Then Background Verification shows "passed", JD Match shows "passed", Panelist Matching shows "running".

**AC-02.8**
Given status is `COMPLETED`,  
When the Stage rows render,  
Then all three stages show "passed" and the "View Interview Readiness Pack" button is visible.

---

### US-03 — Background verification gate

**AC-03.1**
Given a candidate resume contains one or more blocker flags (employment timeline contradiction, unverifiable skill claim with no evidence, contact info malformed, or internal contradiction),  
When the Background Verification Specialist returns `REJECTED`,  
Then the drive status transitions to `REJECTED_BACKGROUND`, the JD Matching Specialist is NEVER called, and the Panelist Matching Specialist is NEVER called.

**AC-03.2**
Given the drive status is `REJECTED_BACKGROUND`,  
When `GET /drives/{id}` is called,  
Then the response contains `background_check.verdict = "REJECTED"`, `background_check.flags` listing at least one entry with `severity = "blocker"`, and `jd_match = null` and `panel_match = null`.

**AC-03.3**
Given the drive status is `REJECTED_BACKGROUND`,  
When the Drive Status screen renders,  
Then the Background Verification row shows status "rejected", the blocker flags are listed below the row (each showing severity and message), and the JD Match and Panelist Matching rows remain greyed/pending.

---

### US-04 — JD matching gate (reject)

**AC-04.1**
Given the background check returned `LEGITIMATE`  
And the JD Matching Specialist returns recommendation `REJECT`,  
When the backend processes the result,  
Then the drive status transitions to `REJECTED_FIT`, the Panelist Matching Specialist is NEVER called.

**AC-04.2**
Given the drive status is `REJECTED_FIT`,  
When `GET /drives/{id}` is called,  
Then the response contains `jd_match.recommendation = "REJECT"`, `jd_match.score` (integer 0–100), `jd_match.missing` (array of skill strings), and `panel_match = null`.

**AC-04.3**
Given the drive status is `REJECTED_FIT`,  
When the Drive Status screen renders,  
Then the JD Match row shows status "rejected", the detail card shows the fit score and missing skills, and the Panelist Matching row remains greyed/pending.

---

### US-05 — JD matching gate (hold)

**AC-05.1**
Given the background check returned `LEGITIMATE`  
And the JD Matching Specialist returns recommendation `HOLD`,  
When the backend processes the result,  
Then the drive status transitions to `HOLD_FIT`, the Panelist Matching Specialist is NEVER called.

**AC-05.2**
Given the drive status is `HOLD_FIT`,  
When `GET /drives/{id}` is called,  
Then the response contains `jd_match.recommendation = "HOLD"`, `jd_match.score`, `jd_match.missing`, and `panel_match = null`.

**AC-05.3**
Given the drive status is `HOLD_FIT`,  
When the Drive Status screen renders,  
Then the JD Match row shows status "hold", the detail card shows score, gaps, and the message "Cancel and resubmit with an updated JD or candidate profile to proceed."

---

### US-06 — Panelist matching and Interview Readiness Pack

**AC-06.1**
Given the background check returned `LEGITIMATE` and JD match returned `PROCEED`,  
When the Panelist Matching Specialist runs,  
Then panelists are first ranked by skill overlap (panelists with zero overlap are excluded outright) and then filtered by availability — the ranking order is NEVER relaxed to satisfy availability.

**AC-06.2**
Given two panelists with equal skill overlap where panelist A has availability and panelist B does not,  
When panelist matching runs,  
Then panelist A is selected and panelist B is excluded — the skill-ranked order is preserved.

**AC-06.3**
Given a selected panelist's `location` matches the candidate's `location`,  
When mode is assigned,  
Then `mode = "In-Person"` and the reason field states the location match.

**AC-06.4**
Given a selected panelist's `location` does NOT match the candidate's `location`,  
When mode is assigned,  
Then `mode = "Online"` and the reason field states the location mismatch.

**AC-06.5**
Given a panel slate has two panelists — one local and one remote,  
When mode is assigned,  
Then each panelist receives its own mode independently (mixed-mode panel is valid).

**AC-06.6**
Given the drive status is `COMPLETED`,  
When `GET /drives/{id}/report` is called (default `format=json`),  
Then the response matches the report JSON shape defined in §5.6 and all fields required by ReadinessPack.jsx are present.

---

### US-07 — Empty panel slate

**AC-07.1**
Given no panelist clears both skill overlap and availability criteria,  
When panelist matching completes,  
Then `panel_match.panel_slate = []` and the drive status is still `COMPLETED` (not an error).

**AC-07.2**
Given `panel_match.panel_slate` is empty,  
When the Interview Readiness Pack screen renders,  
Then the panel table is replaced by the explicit message: "No panelist cleared both skill overlap and availability criteria. Consider updating the panelist pool or interview window." — no empty table rows.

---

### US-08 — DOCX export

**AC-08.1**
Given the drive status is `COMPLETED`,  
When the recruiter clicks "Export (DOCX)",  
Then the browser opens `GET /drives/{id}/report?format=docx` in a new tab and receives a binary file with content-type `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

---

### US-09 — Panelist pool management

**AC-09.1**
Given the recruiter opens the Panelist Pool screen,  
When `GET /panelists` responds,  
Then the table renders one row per panelist showing name, location, skills (tag list), and availability slots.

**AC-09.2**
Given the recruiter edits the JSON in the pool editor and clicks "Save Pool",  
When the JSON is not valid,  
Then the error "Invalid JSON — fix the syntax and try again." is shown and `PUT /panelists` is NOT called.

**AC-09.3**
Given the recruiter edits the JSON and the parsed value is not an array,  
When validation runs,  
Then the error "Pool must be a JSON array." is shown and `PUT /panelists` is NOT called.

**AC-09.4**
Given a valid JSON array is submitted via "Save Pool",  
When `PUT /panelists` responds with the updated pool,  
Then the table refreshes with the new pool and a "Pool saved successfully." banner appears.

---

### US-10 — Drive error / retry

**AC-10.1**
Given the Anthropic API returns an error mid-drive,  
When the backend handles the error,  
Then the drive status transitions to `FAILED` with the error message in `drive.error`, and no further specialist calls are made.

**AC-10.2**
Given the drive status is `FAILED`,  
When the Drive Status screen renders,  
Then the error message is displayed and a "Start New Drive" button is visible (the recruiter may reuse the already-created candidate and job IDs by submitting a new `POST /drives`).

**AC-10.3**
Given a poll returns an HTTP error (network issue or 5xx),  
When the Drive Status screen handles the error,  
Then polling stops, the error message is displayed, and a "Start New Drive" button is shown.

---

## 5. Data Contracts

All request and response bodies are `application/json` unless noted. Base URL: configurable via `VITE_API_URL` (default `http://localhost:8000`).

---

### 5.1 `POST /candidates`

**Request**
```json
{ "resume_text": "<string, required, non-empty>" }
```

**Response 200**
```json
{ "candidate_id": "<string>" }
```

**Response 400** — blank or whitespace-only `resume_text`
```
HTTP 400 — plain text or JSON error message
```

_Derived from: `api.js` `createCandidate`, `NewDrive.jsx` `handleSubmit` destructuring `{ candidate_id }`._

---

### 5.2 `POST /jobs`

**Request**
```json
{ "jd_text": "<string, required, non-empty>" }
```

**Response 200**
```json
{ "job_id": "<string>" }
```

**Response 400** — blank or whitespace-only `jd_text`
```
HTTP 400 — plain text or JSON error message
```

_Derived from: `api.js` `createJob`, `NewDrive.jsx` destructuring `{ job_id }`._

---

### 5.3 `GET /panelists`

**Response 200** — array; empty array `[]` is valid when no pool is loaded.
```json
[
  {
    "id": "<string>",
    "name": "<string>",
    "skills": ["<string>", "..."],
    "location": "<string>",
    "availability": [
      { "date": "<string>", "slots": ["<string>", "..."] }
    ]
  }
]
```

_Derived from: `api.js` `getPanelists`, `PanelistPool.jsx` table columns (name, location, skills, availability), `NewDrive.jsx` `Array.isArray(pool)` guard, `PanelistPool.jsx` required fields hint (id, name, skills, location, availability)._

---

### 5.4 `PUT /panelists`

**Request** — same array shape as `GET /panelists` response (full replacement, not a patch).
```json
[
  {
    "id": "<string>",
    "name": "<string>",
    "skills": ["<string>", "..."],
    "location": "<string>",
    "availability": [
      { "date": "<string>", "slots": ["<string>", "..."] }
    ]
  }
]
```

**Response 200** — the stored pool (same shape as GET); the frontend uses this to refresh the table.
```json
[ /* same array shape */ ]
```

_Derived from: `api.js` `updatePanelists(pool)` sends the array as the body; `PanelistPool.jsx` `setPool(updated)` from the response._

---

### 5.5 `POST /drives`

**Request**
```json
{ "candidate_id": "<string>", "job_id": "<string>" }
```

**Response 200**
```json
{ "drive_id": "<string>" }
```

_Derived from: `api.js` `createDrive`, `NewDrive.jsx` destructuring `{ drive_id }`._

Note: `backend.md` says the initial status is `PENDING`; the frontend does not destructure a `status` field from this response — it polls `GET /drives/{id}` for status. The backend MAY include `"status": "PENDING"` for clarity but the frontend does not depend on it.

---

### 5.6 `GET /drives/{id}`

**Response 200**

```json
{
  "drive_id": "<string>",
  "status": "<DriveStatus enum — see §6>",
  "background_check": {
    "verdict": "LEGITIMATE | REJECTED",
    "flags": [
      { "severity": "blocker | minor | none", "message": "<string>" }
    ]
  } | null,
  "jd_match": {
    "score": "<integer 0–100>",
    "recommendation": "PROCEED | HOLD | REJECT",
    "missing": ["<string>", "..."],
    "must_have": [
      { "skill": "<string>", "status": "met | partial | missing" }
    ],
    "nice_to_have": [
      { "skill": "<string>", "status": "met | partial | missing" }
    ]
  } | null,
  "panel_match": {
    "panel_slate": [
      {
        "name": "<string>",
        "skill_overlap": "<string>",
        "availability_slot": "<string>",
        "mode": "In-Person | Online",
        "reason": "<string>"
      }
    ]
  } | null,
  "error": "<string>" | null
}
```

**Fields consumed by `DriveStatus.jsx`:**
- `drive.status` — determines stage row states and which detail card to render.
- `drive.background_check.verdict` — rendered in `bgSummary()`.
- `drive.background_check.flags[].severity` — counted for blocker summary; used to CSS-class each flag row.
- `drive.background_check.flags[].message` — rendered per flag in the rejection card and `StageRow` flags list.
- `drive.jd_match.score` — rendered in `jdSummary()` and rejection/hold detail cards.
- `drive.jd_match.recommendation` — drives `jdSummary()` text.
- `drive.jd_match.missing[]` — string array rendered as comma-joined list in rejection and hold cards.
- `drive.panel_match.panel_slate[]` — length used in `panelSummary()`.
- `drive.error` — rendered in the FAILED detail card.

**Fields additionally consumed by `ReadinessPack.jsx`** (from `GET /drives/{id}/report`):
- `report.jd_match.must_have[].skill`, `.status` — JD Fit Breakdown table; status values `"met"`, `"partial"`, `"missing"`.
- `report.jd_match.nice_to_have[].skill`, `.status` — same table.
- `report.panel_match.panel_slate[].name`, `.skill_overlap`, `.availability_slot`, `.mode`, `.reason` — panel table columns.

> **Contract mismatch noted:** `GET /drives/{id}` (drive polling) and `GET /drives/{id}/report` (readiness pack) are separate endpoints. `DriveStatus.jsx` calls `getDrive()` only; `ReadinessPack.jsx` calls `getDriveReport()` only. The report endpoint MUST include `must_have` and `nice_to_have` inside `jd_match`, but the polling endpoint only needs `score`, `recommendation`, and `missing`. Backends that return identical shapes for both are fine; backends that return minimal shapes must ensure the report endpoint is richer.

---

### 5.7 `GET /drives/{id}/report`

**Query param:** `format` — `"json"` (default) or `"docx"`.

**Response 200 (format=json)** — same top-level shape as `GET /drives/{id}`, but `jd_match` and `panel_match` must be fully populated (see §5.6 for all fields `ReadinessPack.jsx` reads).

**Response 200 (format=docx)** — binary blob; content-type `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

_Derived from: `api.js` `getDriveReport` and `openDriveReportDownload`; `ReadinessPack.jsx` field access._

---

### 5.8 Drive Status Enum

```
PENDING
RUNNING_BACKGROUND_CHECK
REJECTED_BACKGROUND           ← terminal
RUNNING_JD_MATCH
REJECTED_FIT                  ← terminal
HOLD_FIT                      ← terminal (unless re-submitted)
RUNNING_PANEL_MATCH
COMPLETED                     ← terminal
FAILED                        ← terminal (Anthropic API error)
```

_Derived from: `DriveStatus.jsx` `TERMINAL` set (REJECTED_BACKGROUND, REJECTED_FIT, HOLD_FIT, COMPLETED, FAILED) and `deriveStages()` switch logic._

> **Backend.md discrepancy:** `backend.md` does not list `FAILED` in its status model. The frontend explicitly handles `FAILED` as a terminal status with a separate error card. The backend MUST support `FAILED` as a valid status value.

---

### 5.9 Panelist Pool Item Shape (for `synthetic-data/panelist-pool.json`)

```json
{
  "id": "<string — unique>",
  "name": "<string>",
  "skills": ["<string>", "..."],
  "location": "<string — city or region>",
  "availability": [
    { "date": "<string — e.g. 'Tue 2pm' or 'YYYY-MM-DD'>", "slots": ["<string>", "..."] }
  ]
}
```

_Derived from: `architecture.md` data contract + `PanelistPool.jsx` table rendering and required-fields hint._

---

## 6. Drive Status State Machine

```
                    ┌──────────┐
            create  │  PENDING  │
   POST /drives ──► └──────────┘
                         │ background specialist starts
                         ▼
               ┌────────────────────────┐
               │ RUNNING_BACKGROUND_CHECK│
               └────────────────────────┘
                    │               │
              LEGITIMATE          REJECTED
                    │               │
                    ▼               ▼
           ┌─────────────┐  ┌──────────────────────┐
           │RUNNING_JD_MATCH│  │ REJECTED_BACKGROUND  │ ← TERMINAL
           └─────────────┘  └──────────────────────┘
                  │      │      │
              PROCEED   HOLD  REJECT
                  │      │      │
                  │      ▼      ▼
                  │  ┌─────────┐ ┌────────────┐
                  │  │HOLD_FIT │ │REJECTED_FIT│ ← TERMINAL
                  │  └─────────┘ └────────────┘
                  │    TERMINAL
                  ▼
        ┌─────────────────────┐
        │  RUNNING_PANEL_MATCH │
        └─────────────────────┘
               │          │
           success      API error
               │          │
               ▼          ▼
         ┌──────────┐  ┌────────┐
         │ COMPLETED │  │ FAILED │ ← TERMINAL
         └──────────┘  └────────┘
              TERMINAL
```

### Legal Transitions (exhaustive)

| From | To | Trigger |
|------|----|---------|
| PENDING | RUNNING_BACKGROUND_CHECK | Background specialist invoked |
| RUNNING_BACKGROUND_CHECK | REJECTED_BACKGROUND | Specialist returns REJECTED |
| RUNNING_BACKGROUND_CHECK | RUNNING_JD_MATCH | Specialist returns LEGITIMATE |
| RUNNING_JD_MATCH | REJECTED_FIT | Specialist returns REJECT |
| RUNNING_JD_MATCH | HOLD_FIT | Specialist returns HOLD |
| RUNNING_JD_MATCH | RUNNING_PANEL_MATCH | Specialist returns PROCEED |
| RUNNING_PANEL_MATCH | COMPLETED | Panel slate written to report.json |
| RUNNING_PANEL_MATCH | FAILED | Anthropic API error |
| RUNNING_BACKGROUND_CHECK | FAILED | Anthropic API error |
| RUNNING_JD_MATCH | FAILED | Anthropic API error |
| (any non-terminal) | FAILED | Unhandled exception in background task |

### Terminal Statuses (no further transitions)

- `REJECTED_BACKGROUND`
- `REJECTED_FIT`
- `HOLD_FIT`
- `COMPLETED`
- `FAILED`

---

## 7. Open Questions

The following questions were identified in `architecture.md` or arise from contract analysis and require a human decision before the corresponding feature can be built.

**OQ-1 — Blocker definition (architecture.md)**  
Should *any single unverifiable claim* reject a candidate, or only explicit *contradictions*? Currently the spec says "a claimed skill with zero supporting evidence anywhere in the history is a flag" but does not specify whether this alone triggers REJECTED or only counts as `minor`. **Decision needed:** define the exact threshold for `blocker` severity.

**OQ-2 — Interview window definition (architecture.md)**  
Is availability checked against a **single proposed interview date** supplied by the recruiter, or does the swarm **propose a date from the panelist's own availability** slots? Currently the frontend has no date-picker field, implying the swarm selects from panelist availability autonomously. Confirm this assumption so the Panelist Matching Specialist's output format for `availability_slot` is correct.

**OQ-3 — HOLD handling (architecture.md)**  
Should a `HOLD` from JD Matching pause and wait for human input (interactive mode, requiring a new API action to resume), or should the coordinator autonomously pick a default (proceed or reject) for the demo? The current frontend treats `HOLD_FIT` as a terminal state with a "cancel and resubmit" message — this implies **autonomous terminal HOLD** for the demo. Confirm.

**OQ-4 — `FAILED` status (contract mismatch)**  
`backend.md` does not define `FAILED` as a drive status, but the frontend `DriveStatus.jsx` explicitly handles it (TERMINAL set, error card, polling stop). The backend must emit `"status": "FAILED"` and include `"error": "<message>"` in the drive payload. Confirm this is intended and document it in `backend.md`.

**OQ-5 — Report vs. drive endpoint shape**  
`GET /drives/{id}` and `GET /drives/{id}/report` are separate calls. Should they return identical JSON or can the report endpoint be a superset? Currently `must_have`/`nice_to_have` skill breakdown is only consumed by `ReadinessPack.jsx` (report endpoint) and not by `DriveStatus.jsx` (drive endpoint). Decide whether the drive endpoint should carry the full breakdown too (simpler backend, larger poll payloads) or only the report endpoint carries it (leaner polling).

**OQ-6 — SSE events endpoint scope**  
`GET /drives/{id}/events` is listed in `backend.md` as a planned endpoint but is not called anywhere in the current frontend (polling is used instead). Decide whether this is in scope for the initial build or a stretch goal, and confirm that removing it does not affect any acceptance criteria.

**OQ-7 — `skill_overlap` field format**  
`ReadinessPack.jsx` renders `p.skill_overlap` as a raw string in the panel table. `architecture.md` specifies "skill-overlap %" suggesting a formatted value like `"4/4 skills"` or `"75%"`. Define the exact format so the coordinator's synthesis prompt produces it consistently.

**OQ-8 — `availability_slot` field format**  
`ReadinessPack.jsx` renders `p.availability_slot` as a raw string. The frontend.md example shows `"Tue 2pm"`. Define whether this comes from the panelist's `availability[].date` + `slots[]` directly (e.g. `"Tue 2pm"`) or is synthesized by the coordinator into a different format.
