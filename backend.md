# Backend — Recruitment Drive API

Wraps the Recruitment Drive Swarm (see [architecture.md](./architecture.md)) behind
an HTTP API so a frontend (or any other client) can trigger a drive, watch it
progress through the gated pipeline, and read back the final Interview
Readiness Pack — without talking to the Anthropic SDK directly.

## Why a backend layer at all

The existing scripts (`create_recruitment_specialists.py`,
`create_recruitment_coordinator.py`, `run_recruitment_drive.py`) are one-shot
CLI tools: run once, print to stdout, write to `outputs/`. A backend turns
that into something a UI can drive repeatedly, for different candidates, with
status that can be polled or streamed.

## Stack

- **FastAPI** (matches the Python-first nature of the rest of this repo;
  async support makes streaming the coordinator's event stream straightforward)
- **Anthropic SDK**, reusing the agent/session creation logic already proven
  out in `create_recruitment_coordinator.py` / `run_recruitment_drive.py`
- **Storage:** flat JSON files under `data/` for the hackathon/demo scope —
  same pattern this repo already uses (`.specialist_ids.json`,
  `.coordinator_id`). No database needed unless this goes to production.

## Resources

| Resource | Notes |
| --- | --- |
| Candidate | resume/profile text + parsed location, submitted once per drive |
| Job | the JD text + must-have/nice-to-have skills |
| Panelist pool | skills, location, availability — uploaded or edited in bulk |
| Drive | one run of the pipeline against one candidate + one job |

## Endpoints

```
POST   /candidates              create candidate (resume text) -> candidate_id
POST   /jobs                    create job (JD text)            -> job_id
PUT    /panelists                replace the panelist pool (bulk)
GET    /panelists                read current panelist pool

POST   /drives                  { candidate_id, job_id } -> drive_id, status=running
GET    /drives/{id}             current status + per-stage results
GET    /drives/{id}/events      SSE stream of swarm events (stage transitions, specialist replies)
GET    /drives/{id}/report      final Interview Readiness Pack (JSON, or docx if requested)
```

## Drive status model

Mirrors the gated pipeline in architecture.md — the status is not just
`running`/`done`, it names *where* the pipeline stopped:

```
PENDING
RUNNING_BACKGROUND_CHECK
REJECTED_BACKGROUND          (terminal)
RUNNING_JD_MATCH
REJECTED_FIT                 (terminal)
RUNNING_PANEL_MATCH          (also reached on a HOLD recommendation — the
                               coordinator proceeds to panel matching on HOLD
                               so the hiring manager has the full picture;
                               `jd_match.recommendation` stays "HOLD" in the
                               report so this isn't confused with PROCEED)
COMPLETED                    (terminal — report available)
```

`GET /drives/{id}` returns the current status plus whichever stage results
have completed so far, e.g.:

```json
{
  "drive_id": "drv_123",
  "status": "RUNNING_PANEL_MATCH",
  "background_check": { "verdict": "LEGITIMATE", "flags": [] },
  "jd_match": { "score": 82, "recommendation": "PROCEED", "missing": ["Kubernetes"] },
  "panel_match": null
}
```

## How a drive executes

1. `POST /drives` loads the candidate + job text, creates an Anthropic
   session against the Recruitment Drive Lead coordinator (same call shape as
   `run_deal_desk.py`'s `client.beta.sessions.create`), and returns
   immediately with `status=PENDING`.
2. A background task drives the session, same event-stream loop as
   `run_deal_desk.py`, but instead of printing to stdout it updates the
   drive's status file as each gate resolves (background check verdict → JD
   match result → panel match result).
3. If a gate fails (`REJECTED_BACKGROUND` / `REJECTED_FIT`), the background
   task stops early and does not invoke the remaining specialists — this
   must be enforced in the coordinator's system prompt *and* checked by the
   backend, since a model could in principle ignore the instruction.
4. On `COMPLETED`, the synthesized Interview Readiness Pack is written to
   `data/drives/{id}/report.json` (and optionally rendered to docx via the
   same skill-based approach as the Deal Desk's branded document).

## Error handling

- Malformed/empty resume or JD text → `400` before a session is even created
  (no point spending a model call on empty input).
- Anthropic API errors mid-drive → status becomes `FAILED` with the error
  message attached; the frontend should let the user retry the drive without
  re-uploading candidate/job data.

## Out of scope for the demo

Auth, multi-tenancy, a real database, and rate limiting are all deliberately
left out — same hackathon scope as the rest of this repo. Note them here so
they're not forgotten if this gets productionised.
