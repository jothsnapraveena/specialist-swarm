# Architecture — Recruitment Drive Swarm (Card D)

A new scenario card for this repo, following the same coordinator + specialists +
skills pattern as the Deal Desk (Card A). Where Deal Desk fans specialists out in
**parallel**, this swarm is a **sequential, gated pipeline** — each stage decides
whether the next stage runs at all.

## The pipeline

```
                    ┌─────────────────────────┐
                    │   Recruitment Drive Lead  │   (coordinator)
                    └─────────────────────────┘
                                 │
        1. Background Verification Specialist
           input: resume / candidate profile
                                 │
              legitimate? ──No──► REJECTED — stop, emit rejection report
                                 │ Yes
                                 ▼
        2. JD Matching Specialist
           input: candidate profile + job description
                                 │
              fit acceptable? ──No──► HOLD/REJECT — stop, emit fit report
                                 │ Yes
                                 ▼
        3. Panelist Matching Specialist
           input: candidate skills (from JD match) + panelist pool
           a) rank panelists by SKILL overlap        (1st criterion)
           b) filter ranked panelists by AVAILABILITY (2nd criterion)
           c) for each selected panelist:
                candidate.location == panelist.location → In-Person
                else                                     → Online
                                 │
                                 ▼
        Coordinator synthesises: Interview Readiness Pack
        (verdict, JD fit summary, panel slate with mode + reasoning)
```

Stages 2 and 3 only run if the prior gate passes — the coordinator must call
specialists **in order, not in parallel**, and must stop early on a rejection.
This is the main divergence from Card A's "delegate to all four at once" pattern.

## Coordinator

**Name:** Recruitment Drive Lead
**Model:** claude-opus-4-7 (synthesis + gating judgment)

Responsibilities:
- Read the candidate profile and JD itself first.
- Call Background Verification Specialist. If verdict is `REJECTED`, stop and
  produce a short rejection report — do not call the other two specialists.
- If `LEGITIMATE`, call JD Matching Specialist. If recommendation is `REJECT`,
  stop and produce a fit report. If `HOLD`, surface the gaps and ask the user
  whether to proceed.
- If `PROCEED`, call Panelist Matching Specialist with the candidate's
  required-skill set and the panelist pool.
- Synthesise everything into one **Interview Readiness Pack**:
  1. Verdict (background check result)
  2. JD fit summary (score, matched/missing skills)
  3. Recommended panel — each panelist with skill-overlap %, availability
     window used, and interview mode (In-Person / Online) with the reason
  4. Fallback note if no panelist cleared both criteria

## Specialists

### 1. Background Verification Specialist
**Skill:** `resume-verification-checklist`
**Model:** claude-sonnet-4-6

Inputs: candidate resume / profile text.
Checks (textual, not document-forensics):
- Employment timeline consistency (no overlapping/contradictory dates, no
  unexplained gaps inconsistent with stated narrative)
- Education and certification claims are internally consistent and plausible
  for the stated timeline
- Skill claims are corroborated by described employment/projects (a claimed
  skill with zero supporting evidence anywhere in the history is a flag)
- Contact info is well-formed (valid email/phone shape)
- No internal contradictions (e.g., two different "current employers")

Output: `LEGITIMATE` or `REJECTED`, plus a list of flags with severity
(`blocker` / `minor` / `none`). A single blocker ⇒ `REJECTED`.

### 2. JD Matching Specialist
**Skill:** `jd-matching-rubric`
**Model:** claude-sonnet-4-6

Inputs: job description + (verified) candidate profile.
Output:
1. Fit score 0–100
2. Must-have skills: met / partially met / missing
3. Nice-to-have skills: met / missing
4. Recommendation: `PROCEED` / `HOLD` / `REJECT`

### 3. Panelist Matching Specialist
**Skill:** `panelist-matching-policy`
**Model:** claude-sonnet-4-6

Inputs: candidate's required-skill set (from JD match) + panelist pool
(skills, location, availability).

Decision order is fixed and must not be reordered:
1. **Skill match (primary):** rank panelists by overlap between panelist
   skills and the candidate's required/matched skill set. Panelists with no
   overlap are excluded outright.
2. **Availability (secondary):** among skill-ranked panelists, keep only
   those with an open slot in the interview window. If the top skill-ranked
   panelist has no availability, move down the ranked list — never relax the
   skill criterion to satisfy availability.
3. **Mode assignment:** for each selected panelist, compare
   `candidate.location` to `panelist.location`. Match → `In-Person`.
   Mismatch → `Online`. This is assigned per-panelist, not once per slate,
   since a panel can be mixed-mode.

Output: ranked panel slate (typically 2–3 panelists) with skill-overlap %,
availability slot used, and mode + reason. If nobody clears both criteria,
say so explicitly rather than forcing a weak match.

## Data contracts

`synthetic-data/candidate-profile.md` — resume-style markdown: name, contact,
location, education, employment history (company/title/start/end), skills.

`synthetic-data/sample_jd.md` — job title, location/remote policy, must-have
skills, nice-to-have skills, experience level.

`synthetic-data/panelist-pool.json` — array of
`{ id, name, skills: [...], location, availability: [ {date, slots} ] }`.

## File layout (to be built)

Mirrors Card A's file set, additive — does not touch the Deal Desk files:

```
skills/
├── resume-verification-checklist/SKILL.md
├── jd-matching-rubric/SKILL.md
└── panelist-matching-policy/SKILL.md
synthetic-data/
├── candidate-profile.md
├── sample_jd.md
└── panelist-pool.json
create_recruitment_specialists.py   (mirrors create_specialists.py)
create_recruitment_coordinator.py   (mirrors create_coordinator.py; system prompt enforces sequential gating, not parallel fan-out)
upload_recruitment_skills.py        (mirrors upload_skills.py)
run_recruitment_drive.py            (mirrors run_deal_desk.py)
```

## Open questions before building

- What counts as a "blocker" in background verification — should any single
  unverifiable claim reject a candidate, or only contradictions?
- Interview window: is availability checked against a single proposed date,
  or does the swarm need to propose a date from panelist availability?
- Should a `HOLD` from JD matching pause for human input, or should the
  coordinator pick a default (proceed/reject) autonomously for the demo?
