# Product Requirements Document — Talent Cortex

**Version:** 1.0  
**Date:** 2026-06-17  
**Status:** Draft — MVP  
**Product Name:** Talent Cortex

---

## 1. Product Overview & Vision

Talent Cortex is a recruiter-facing web application that automates the pre-interview evaluation of a candidate against a job description. It wraps a three-stage AI swarm — Background Verification, JD Matching, and Panelist Matching — behind a clean, single-purpose interface. The recruiter pastes a resume and job description, submits a recruitment drive, and Talent Cortex orchestrates a coordinated sequence of AI specialists that gate the candidate through each stage. The output is an **Interview Readiness Pack**: a fully-reasoned recommendation covering the suggested interview panel, skill-overlap rationale, available time slots, and recommended interview mode.

The vision is to compress what today takes a recruiter multiple manual steps and several business days into a five-minute, auditable, AI-driven workflow — one that surfaces the right panel for the right candidate, every time.

---

## 2. Target Users / Personas

| Persona | Role | Primary Need |
|---|---|---|
| **Talent Recruiter (Primary)** | Owns the recruitment drive from submission to scheduling | Quickly determine if a candidate is worth interviewing and which panelists should conduct it |
| **Hiring Manager (Secondary)** | Consumes the Interview Readiness Pack to make the final scheduling call | Understand fit rationale and panel composition without re-reading the resume |

The recruiter is the sole actor in the Talent Cortex UI. The hiring manager is an indirect consumer of the exported Interview Readiness Pack.

---

## 3. Problem Statement

### Current Manual Pain

Recruiters today juggle multiple tools to evaluate a single candidate: they manually compare resumes against job descriptions, chase panelist calendars across email and calendar apps, and rely on personal judgment — or undocumented tribal knowledge — to match a candidate's background to the right interviewer skill set. Background plausibility checks (timeline gaps, inconsistent titles, unverifiable credentials) are informal and inconsistent.

The result is high recruiter effort per hire, inconsistent candidate evaluation quality, slow time-to-panel-assignment, and a risk of bias from unstructured decision-making.

### What Talent Cortex Automates

Talent Cortex replaces this multi-tool, judgment-heavy process with a sequentially-gated AI swarm. The Background Verification specialist audits the resume for internal consistency and public profile alignment. The JD Matching specialist scores the candidate against the structured requirements of the job description, with explicit scoring rules for must-have and nice-to-have skills. The Panelist Matching specialist selects and ranks panelists by skill overlap, availability, and location — returning a fully-justified panel slate. Each gate is an explicit pass/hold/reject decision, not a vague recommendation.

---

## 4. Goals

1. **Reduce time-to-readiness-pack** from multiple business days to under 5 minutes for a submitted drive.
2. **Eliminate unstructured background review** by enforcing a consistent, bias-guarded two-lane background verification on every candidate.
3. **Standardize JD fit scoring** with a transparent, rule-based rubric (must-have vs nice-to-have weights, threshold bands) that is reproducible across recruiters.
4. **Surface the optimal panel** automatically — removing the need for manual calendar chasing and panelist skill look-ups.
5. **Produce a downloadable, shareable Interview Readiness Pack** (DOCX) that a hiring manager can act on without accessing the Talent Cortex UI.
6. **Reduce recruiter rework** by stopping disqualified candidates at the earliest possible gate, surfacing specific rejection flags rather than a binary thumbs-down.

---

## 5. Non-Goals (Demo Scope)

The following are explicitly out of scope for the current release and will not be delivered:

- Authentication and authorization (no login, no role enforcement)
- Multi-tenancy and recruiter-level data isolation
- Persistent database storage (flat JSON files used for demo)
- API rate limiting and quota management
- Cancel or pause a running drive mid-pipeline
- Mobile-responsive UI
- Multi-recruiter simultaneous live views of the same drive
- Document-forensic background checks (the verification is AI-reasoning-based, not database-sourced)

---

## 6. Feature Epics & User Stories

### Epic 1 — Drive Submission

Recruiters paste a candidate resume and job description and submit a new recruitment drive in a single action.

**User Stories:** US-01  
**Key Acceptance Criteria:**  
- Both resume and JD text are required; inline validation prevents submission if either is empty, with no backend call made.  
- Valid inputs trigger parallel creation of the candidate and job records, followed by drive creation, and navigate the recruiter to the Drive Status screen.  
- Backend rejects blank text fields with HTTP 400 before any AI processing begins.

---

### Epic 2 — Live Status Monitoring

Recruiters can watch the pipeline progress stage-by-stage without refreshing.

**User Stories:** US-02  
**Key Acceptance Criteria:**  
- The UI polls drive status every 2,500 milliseconds until a terminal status is reached.  
- A pulsing indicator signals an in-progress stage; polling stops immediately on terminal status.  
- Each stage row (Background, JD Match, Panel Match) correctly reflects its current state: pending, running, passed, or stopped.

---

### Epic 3 — Background Verification Gate

The AI audits the resume across two lanes and makes a pass/reject decision before any JD or panel work begins.

**User Stories:** US-03  
**Key Acceptance Criteria:**  
- A single blocker flag from either lane results in immediate drive rejection; multiple minor flags do not accumulate to a blocker.  
- The JD Match and Panel Match stages are never invoked when a candidate is rejected at this gate.  
- The Drive Status screen displays the specific blocker flags in the Background row; JD and Panel rows remain greyed.  
- The bias guardrail is enforced: protected characteristics are never surfaced as flags.

---

### Epic 4 — JD Matching Gate

The AI scores the candidate against must-have and nice-to-have skills and recommends PROCEED, HOLD, or REJECT.

**User Stories:** US-04, US-05  
**Key Acceptance Criteria:**  
- A REJECT recommendation (score below 45, or two or more must-haves missing) halts the drive; the Panel stage is never invoked; the UI displays fit score and missing skills.  
- A HOLD recommendation (score 45–69, or exactly one must-have missing, even if overall score is 70+) halts the drive; the UI displays score, gaps, and prompts the recruiter to resubmit with an updated JD or candidate profile.  
- A PROCEED recommendation continues the pipeline to panel matching.

---

### Epic 5 — Panelist Matching

The AI selects the best-fit panel from the available pool, ranked by skill overlap, filtered by availability, and assigned an interview mode per panelist.

**User Stories:** US-06, US-07  
**Key Acceptance Criteria:**  
- Panelists are ranked by skill overlap with the required skills; zero-overlap panelists are excluded outright.  
- Among equal-overlap panelists, those with availability take precedence; the skill criterion is never loosened to meet availability.  
- Each panelist receives an independent mode assignment: In-Person when the candidate and panelist locations match, Online otherwise; a mixed-mode panel is valid.  
- When no panelist clears both skill and availability criteria, the panel slate is empty and the drive reaches COMPLETED status (not an error); the UI shows an explicit "no panelist cleared both criteria" message.

---

### Epic 6 — Interview Readiness Pack

The recruiter views and shares a fully-structured recommendation after the drive completes.

**User Stories:** US-06  
**Key Acceptance Criteria:**  
- The pack displays the overall verdict, JD fit table (score, met/partial/missing skills), and panel slate (name, skill overlap %, availability slot, mode, rationale).  
- The pack is only accessible once the drive reaches COMPLETED status.

---

### Epic 7 — Export

The recruiter downloads the Interview Readiness Pack as a formatted DOCX document.

**User Stories:** US-08  
**Key Acceptance Criteria:**  
- Clicking "Export (DOCX)" opens the browser's file download for a binary DOCX file.  
- The download is initiated directly from the browser via the report endpoint; no additional UI steps are required.

---

### Epic 8 — Panelist Pool Management

Recruiters can view and bulk-edit the full panelist pool from within the UI.

**User Stories:** US-09  
**Key Acceptance Criteria:**  
- The pool table renders each panelist's name, location, skills (as tags), and availability slots.  
- Submitting invalid or non-array JSON surfaces a specific error message without calling the update endpoint.  
- A valid JSON array submission updates the pool and confirms success with a banner.

---

### Epic 9 — Error Handling & Retry

When the AI pipeline fails due to an API error, the recruiter is informed clearly and can restart without re-entering data.

**User Stories:** US-10  
**Key Acceptance Criteria:**  
- An Anthropic API error at any stage halts the pipeline, records the error in the drive record, and does not call further specialists.  
- The UI displays the error message and a "Start New Drive" button.  
- If polling itself encounters an HTTP error, polling stops and the recruiter is shown the same recovery path.

---

## 7. The Gated Pipeline (Product View)

### Plain-English Description

When a recruiter submits a drive, Talent Cortex does not evaluate everything at once. It runs the three AI specialists in a strict sequence, and each specialist acts as a gate: only a clear positive result from one stage unlocks the next.

**Stage 1 — Background Verification** audits the resume for internal plausibility (timeline consistency, credential believability, skill corroboration) and public profile alignment. If it finds any blocker-level issue, the drive stops immediately. There is no point scoring the JD fit of a candidate whose background cannot be trusted.

**Stage 2 — JD Matching** scores the candidate against the specific role requirements. Scoring is rules-based: must-have skills carry most of the weight; nice-to-haves fill the remainder. The stage produces one of three outcomes — PROCEED (strong fit), HOLD (borderline, human review needed), or REJECT (insufficient fit). Only a PROCEED continues to stage 3.

**Stage 3 — Panelist Matching** selects the best available panel for a qualified candidate. It ranks panelists by skill overlap, filters by availability, and assigns interview mode based on location. It runs only when the candidate has already passed both earlier gates.

### ASCII Flow

```
POST /drives
     |
     v
[BACKGROUND VERIFICATION]
     |                \
  LEGITIMATE        BLOCKER FLAG
     |                   \
     v                    v
[JD MATCHING]       REJECTED_BACKGROUND (stop)
     |      \     \
  PROCEED  HOLD  REJECT
     |       |      |
     v       v      v
[PANEL    HOLD_FIT  REJECTED_FIT
 MATCH]   (stop)    (stop)
     |
     v
COMPLETED (or FAILED on API error)
```

### Why Sequential, Not Parallel

Running the stages in parallel would waste AI processing on candidates who would have been stopped at an earlier gate. More importantly, the output of each stage is an input to the next: it is meaningless to match a panel against a candidate whose background has not been verified, or to select a panel for a candidate who does not meet the role's requirements. The sequential design encodes a deliberate decision hierarchy.

### What "Gate" Means Operationally

A gate is a decision point that either passes the candidate forward or terminates the drive with a specific, recorded status. A terminated drive retains the stage output that caused the stop, so the recruiter always knows precisely why and where the candidate was rejected or held — not just that the drive ended.

---

## 8. Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Time from drive submission to completed Interview Readiness Pack | < 5 minutes (p90) | Timestamp delta: drive created → COMPLETED status |
| Background gate stop rate | Tracks accuracy of BG specialist; baseline TBD | % of drives ending at REJECTED_BACKGROUND |
| JD Match gate stop rate (REJECT + HOLD) | Calibrated against human reviewer agreement rate ≥ 80% | % of drives ending at REJECTED_FIT or HOLD_FIT |
| Panelist match rate (non-empty slate) | ≥ 70% of COMPLETED drives return at least one panelist | % of COMPLETED drives with panel_slate length > 0 |
| Export usage rate | ≥ 50% of COMPLETED drives result in a DOCX download | Count of export requests / count of COMPLETED drives |
| Recruiter error recovery rate | ≥ 90% of FAILED drives result in a new drive submission within the session | % of FAILED status → next drive submission in same session |
| API pipeline reliability | < 5% of drives reach FAILED status due to API error | % of drives ending at FAILED |

---

## 9. Release Scope (MVP)

The MVP ships all ten user stories (US-01 through US-10) with the following scope:

- Four-screen React UI: New Drive, Drive Status, Interview Readiness Pack, Panelist Pool
- FastAPI backend with flat JSON storage
- Three AI specialists orchestrated via the Anthropic Claude API
- Fully gated pipeline with all terminal statuses surfaced in the UI
- DOCX export of the Interview Readiness Pack
- Bulk panelist pool editing via a JSON textarea
- Error handling and drive retry via "Start New Drive" flow

The MVP is a self-contained, single-recruiter demo suitable for product stakeholder review and technical evaluation. No authentication, persistent database, or multi-tenancy is included.

---

## 10. Future Scope

The following capabilities are planned for post-MVP phases:

- **Authentication & Authorization** — recruiter login, role-based access, and audit trail of who submitted which drive
- **Multi-tenancy** — recruiter-level and organization-level data isolation
- **Persistent Database** — replace flat JSON with a relational or document database for scale and query capability
- **Real-time Push (SSE/WebSocket)** — replace polling with server-sent events for instant stage updates
- **Cancel & Pause** — allow a recruiter to halt a running drive mid-pipeline without data loss
- **Mobile Responsiveness** — support tablet and phone form factors for recruiters reviewing on the go
- **Multi-recruiter Live Views** — multiple recruiters observing the same drive in real time
- **Document-Forensic Background Checks** — integrate with third-party verification APIs (employment history databases, credential verification services) rather than relying solely on AI reasoning
- **Calendar Integration** — connect panelist availability directly to calendar systems rather than managing it via static JSON
- **Analytics Dashboard** — aggregate metrics across drives, recruiters, and roles for workforce planning insight

---

*This document is the authoritative product specification for the Talent Cortex MVP. All implementation decisions should be validated against the acceptance criteria defined in Section 6.*
