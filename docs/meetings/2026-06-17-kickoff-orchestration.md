# Kickoff — Orchestration ↔ All Teams

**Date:** 2026-06-17
**Attendees:** Master Orchestrator, Requirements, Skills, Frontend Lead, Backend Lead, Data, Testing, Review
**Type:** Kickoff / decomposition

## Agenda
- Decompose the Talent Cortex recruitment swarm build into lanes
- Confirm the gated pipeline (Background Check → JD Match → Panel Match)
- Assign ownership and branches

## Decisions
1. **Branches:** `frontend` owns the React console; `feature` owns the swarm +
   skills + synthetic data + backend; `dashboard` is the integration branch
   (`feature` + Flight Deck).
2. **Frontend is fixed** — no new product frontend; the dashboard is a separate
   stdlib telemetry app.
3. **Backend owns the endpoints** — dashboard integrates with their data, does
   not build a competing backend.
4. **Product name:** Talent Cortex.

## Action items
- [x] Requirements: write docs/REQUIREMENTS.md from architecture/backend/frontend
- [x] Skills: author matching + background-check skills
- [ ] Backend: implement endpoints + gated drive engine, write data/ JSON store
- [ ] Data: finalise synthetic data + JSON schema
- [x] Dashboard: build Flight Deck with dummy data, define integration seam
