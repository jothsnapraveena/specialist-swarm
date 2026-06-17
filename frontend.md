# Frontend — Recruitment Drive Console

A recruiter-facing UI that drives the API in [backend.md](./backend.md) and
visualises progress through the gated pipeline in
[architecture.md](./architecture.md). Goal: a recruiter pastes in a resume
and a JD, watches the swarm work through three stages, and gets a panel
recommendation they can act on — no Anthropic console, no JSON reading.

## Stack

- **React + Vite**, plain fetch/SSE — no need for a heavy state library at
  this scope (a handful of screens, one in-flight drive at a time per user)
- Polling `GET /drives/{id}` every 2–3s is good enough for a demo; SSE via
  `GET /drives/{id}/events` is the nicer version if there's time, since it
  reproduces the "watch the swarm move" effect that makes Card A's demo land

## Screens

### 1. New Drive
- Paste-or-upload resume text, paste-or-upload JD text
- Panelist pool is pre-loaded from `GET /panelists` (with an "edit pool"
  link to screen 4) — a recruiter running drives all day shouldn't have to
  re-enter the pool every time
- Submit → `POST /candidates`, `POST /jobs`, `POST /drives` → navigate to
  screen 2 with the new `drive_id`

### 2. Drive Status (the live view)
Three stage rows, each one of: pending / running / passed / **stopped here**:

```
✓  Background Verification    LEGITIMATE
✓  JD Match                   Score 82 — PROCEED
●  Panelist Matching          running...
```

If a gate fails, the row turns into a stop state and the rest of the rows
stay greyed out — this is the main visual difference from Card A's
all-parallel demo: here, *not progressing* is itself meaningful information,
not a wait state. e.g.:

```
✗  Background Verification    REJECTED — 2 blocker flags
   Employment timeline contradicts stated current employer
   [ View full flag report ]
```

### 3. Interview Readiness Pack (on `COMPLETED`)
- Verdict banner (legitimate, fit score)
- JD fit table: must-have skills vs met/partial/missing
- Panel slate table:

  | Panelist | Skill overlap | Availability used | Mode | Why |
  | --- | --- | --- | --- | --- |
  | A. Rao | 4/4 skills | Tue 2pm | In-Person | same location (Bengaluru) |
  | J. Lee | 3/4 skills | Wed 10am | Online | candidate in Bengaluru, panelist remote |

- "No panelist cleared both criteria" empty state, explicit rather than a
  blank table, per architecture.md's instruction not to force a weak match
- Export/download button → `GET /drives/{id}/report` (json or docx)

### 4. Panelist Pool
- Table of panelists: skills (tag list), location, availability slots
- Bulk edit → `PUT /panelists`
- This is the screen that lets a recruiter correct the two inputs that
  actually drive stage 3's decision (skills, availability) without touching
  any code

## Component notes

- Stage row component is shared between screen 2 (live) and screen 3
  (completed summary) — same data shape, different chrome
- Skill-overlap and mode columns in the panel table should show the *reason*
  inline (location match/mismatch, which skills overlapped) rather than just
  the verdict — the recruiter needs to be able to defend the panel pick to a
  candidate or hiring manager without going back to the raw transcript

## Out of scope for the demo

No auth/login, no multi-recruiter views, no editing a drive in place once
it's running (cancel-and-resubmit is fine). Mobile responsiveness not a
priority — this is an internal recruiter tool used at a desk.
