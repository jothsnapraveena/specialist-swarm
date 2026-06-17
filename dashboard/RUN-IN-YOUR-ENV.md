# Run the Talent Cortex dashboard in YOUR (backend) environment

Paste the prompt below into **your Claude Code** session, opened in your local
clone of `specialist-swarm` (on your `feature`/backend branch). It pulls the
dashboard branch, wires the Tracker into the backend, and launches the Flight
Deck so it shows your backend agents working + the recruitment progress live.

---

## Prompt to paste into your Claude

> Integrate the Talent Cortex Flight Deck dashboard into this backend repo and
> run it so it tracks backend agents + recruitment progress live.
>
> 1. Fetch and merge the dashboard branch into my current branch (it only ADDS
>    `dashboard/`, `tracker/`, `docs/`, and one skill — it must not modify my
>    backend files):
>    ```
>    git fetch origin
>    git merge origin/dashboard --no-edit
>    ```
> 2. Read `tracker/progress_tracker.py` and `dashboard/data.json` to learn the
>    contract. Then wire the Tracker into my FastAPI drive engine so that, on
>    every gate transition, it updates `data/progress.json` and `data/agents.json`:
>    - `from tracker.progress_tracker import Tracker` ; `tk = Tracker("data")`
>    - When a candidate/job/drive is created: `tk.upsert_candidate(...)`,
>      `tk.upsert_position(...)`.
>    - As each specialist runs: `tk.record_agent("Drives + Gated Engine",
>      status="running", task="background check for cand_x")`, then
>      `status="done"` with `tokens=...` when it returns. Use the agent names
>      from `dashboard/agent_status.json` (Backend Team members) so they overlay
>      onto Agent Teams.
>    - On each gate result: `tk.set_candidate_stage(id, stage=..., bg_check=...,
>      jd_score=...)`; on finish: `tk.set_candidate_result(id, result=...)`.
>    - When the Panelist agent schedules: `tk.record_interview(...)`.
> 3. Start my backend (e.g. `uvicorn app:app --reload --port 8000`) and run a
>    drive so data is produced under `data/`.
> 4. Launch the dashboard pointed at my live data and confirm it serves:
>    ```
>    DATA_DIR=data PYTHONIOENCODING=utf-8 python dashboard/serve.py
>    ```
>    Open http://localhost:8765 — the Integration tab should show my endpoints,
>    the Agent Teams tab should light up live backend agents, and Candidates /
>    Pipeline / Interviews should reflect real drives.
> 5. Do not change `dashboard/` or `tracker/` logic — only add the Tracker calls
>    inside my backend. Report what you wired and the dashboard URL.

---

## What you'll see

- **Integration tab** — Frontend ↔ Backend API contract with per-endpoint status.
- **Agent Teams** — your backend swarm agents lighting up live (overlay from
  `data/agents.json`).
- **Candidates / Pipeline / Interviews** — real recruitment progress from
  `data/progress.json`.
- **Optimization** — token cost vs human baseline.

If you don't set `DATA_DIR`, the dashboard runs on bundled dummy data so the UI
is still demoable.
