# Talent Cortex — Flight Deck Dashboard

A zero-dependency (Python stdlib only) live dashboard that showcases the
**Talent Cortex** recruitment swarm: the agent fleet, the gated recruitment
pipeline, and the application data (candidates, open positions, panelists &
slots, interviews & results), plus a transparent **cost / ROI optimization**
panel computed from REAL agent token usage.

## Run it

```bash
python dashboard/serve.py            # http://localhost:8765
PORT=9000 python dashboard/serve.py  # custom port
```

Open the URL. The page auto-refreshes every 3s from `/api/state`.

## Files

| File | Role |
| --- | --- |
| `serve.py` | stdlib HTTP server; merges status + data, computes optimization |
| `index.html` | single-file UI (tabs: Overview, Fleet, Pipeline, Candidates, Positions, Panelists, Interviews, Optimization) |
| `agent_status.json` | the agent fleet + tasks, with **real token usage** recorded by the orchestrator |
| `data.json` | **DUMMY** recruitment data — replaced at integration time (see below) |

## How the optimization is computed (transparent)

```
AI cost  = Σ tokens × (0.7 × in_rate + 0.3 × out_rate) / 1e6
Human    = Σ human_hours × $rate/hr        (labelled estimate of manual effort)
Savings  = Human − AI
ROI      = Savings / AI cost
```

Tokens are **actual** sub-agent usage; per-model published rates and the human
baseline are in `agent_status.json`. The number firms up as more agents report.

## Integration plan (how this connects to the team's work)

This dashboard is intentionally decoupled so it can integrate without touching
the frontend (owned by the `frontend` branch) or the backend (owned by the
backend teammate). There are two integration seams — pick whichever the backend
exposes first:

1. **Read the backend's JSON store (recommended for the demo).**
   `backend.md` stores everything as flat JSON under `data/`. Point the
   dashboard at it:
   ```bash
   DATA_DIR=../data python dashboard/serve.py
   ```
   `serve.py` will read `candidates`, `jobs`, `panelists`, and `drives` from
   that folder and fall back to `data.json` for anything missing. (Field mapping
   is finalised once the backend's on-disk shapes are pushed.)

2. **Proxy the backend API.**
   Set `BACKEND_URL=http://localhost:8000`; `serve.py` will call the live
   endpoints (`GET /panelists`, `GET /drives/...`) to show in-flight drive
   progress. Note: showing *list of candidates / positions* needs list
   endpoints the current contract doesn't yet expose — coordinate with backend
   to add `GET /candidates`, `GET /jobs`, `GET /drives`.

Until either seam is wired, the dashboard runs on `data.json` dummy data so the
UI and the optimization panel are demoable today.

## Branch / collaboration model

- `frontend` — the React recruiter console (frontend teammate)
- `feature` — the swarm + skills + synthetic data + backend (backend teammate)
- `dashboard` — **integration branch**: `feature` + this flight deck. Rebased on
  `feature` so it always carries the latest backend/swarm. Merge `frontend` in
  at demo time for the full product.
