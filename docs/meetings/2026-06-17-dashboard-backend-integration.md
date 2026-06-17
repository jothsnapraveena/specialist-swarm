# Integration Sync — Dashboard ↔ Backend

**Date:** 2026-06-17
**Attendees:** Master Orchestrator (Integration Coordinator), Backend Team Lead
**Type:** Integration / contract

## Problem
The Flight Deck needs a real data source to show live progress. We are working
in separate branches, so without a shared contract the dashboard has nothing to
display beyond dummy data.

## Options discussed
1. **Backend writes a flat JSON store under `data/`** (already in backend.md).
   Dashboard reads it via `DATA_DIR=../data`. ✅ Recommended — lowest coupling.
2. **Backend exposes list endpoints** (`GET /drives`, `GET /candidates`,
   `GET /jobs`) + existing `GET /panelists`. Dashboard proxies via `BACKEND_URL`.
3. **A Tracker Agent** in the backend that appends pipeline events
   (stage transitions, verdicts) to `data/progress.json` — a single, stable file
   the dashboard polls.

## Decision
Adopt **(1) + (3)**: backend writes `data/drives/{id}/status.json` per drive AND
a rolling `data/progress.json` (via a lightweight Tracker Agent / background-task
hook). Dashboard's `serve.py` already has the `DATA_DIR` seam; it will read these.

## Contract for `data/progress.json` (proposed)
```json
{
  "candidates": [ { "id", "name", "position", "stage", "result", "jd_score" } ],
  "open_positions": [ { "id", "title", "location", "status", "openings", "must_have" } ],
  "panelists": [ { "id", "name", "location", "skills", "availability" } ],
  "interviews": [ { "candidate", "position", "panel", "mode", "datetime", "status", "result" } ],
  "pipeline_summary": { "background_check", "jd_match", "panel_match", "interviewing", "selected", "rejected" }
}
```

## Action items
- [ ] Backend: add Tracker Agent that writes `data/progress.json` on each gate
- [ ] Dashboard: map `data/progress.json` → `/api/state.data` (seam ready)
- [ ] Both: keep field names identical to dashboard/data.json (this dummy file is
      the agreed shape)
