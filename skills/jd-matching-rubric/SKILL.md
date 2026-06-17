---
name: jd-matching-rubric
description: Scoring rubric for matching a verified candidate profile against a job description. Use whenever asked to assess fit, score a candidate against a JD, or decide whether a candidate should proceed to panel matching. Trigger on any request to compute a fit score, compare candidate skills to job requirements, or recommend proceed/hold/reject on a candidate.
---

# JD Matching Rubric

Only run this on a candidate the Background Verification Specialist has
already marked `LEGITIMATE`. Your job is a single fit score plus a clear
recommendation — not a rewrite of the resume.

## Scoring

Score 0–100, built from two weighted buckets:

- **Must-have skills — 70 points total.** Split evenly across the JD's
  must-have list. Each must-have is `met` (full points), `partial` (half
  points — candidate has adjacent/weaker experience), or `missing` (zero).
- **Nice-to-have skills — 30 points total.** Split evenly across the JD's
  nice-to-have list. Same met/partial/missing scoring.

Round to the nearest integer.

## Recommendation thresholds

| Condition | Recommendation |
| --- | --- |
| Score ≥ 70 AND zero must-haves `missing` | `PROCEED` |
| Score 45–69, OR exactly one must-have `missing` | `HOLD` |
| Score < 45, OR two or more must-haves `missing` | `REJECT` |

A single `missing` must-have caps the recommendation at `HOLD` even if the
score alone would clear 70 — must-haves gate the decision, the score doesn't
override them.

## Output format

```
SCORE: <0-100>
MUST-HAVE:
- <skill>: met | partial | missing — <one-line evidence from the candidate profile>
NICE-TO-HAVE:
- <skill>: met | partial | missing
RECOMMENDATION: PROCEED | HOLD | REJECT
REQUIRED_SKILLS_FOR_PANEL: <comma-separated list of the must-have skills that
  were met or partial — this is the exact list the Panelist Matching
  Specialist will rank panelists against>
```

`REQUIRED_SKILLS_FOR_PANEL` must use the same skill names the panelist pool
uses (don't paraphrase — e.g. write "Kubernetes" not "container orchestration"
unless the panelist pool itself uses the paraphrase).
