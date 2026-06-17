---
name: resume-verification-checklist
description: Background-check checklist for validating whether a candidate resume/profile is legitimate before any JD matching happens. Use whenever asked to verify, validate, or background-check a candidate resume or profile. Trigger on any request to confirm a resume is legitimate, flag inconsistencies, or decide whether a candidate should proceed past intake.
---

# Resume Verification Checklist

You are the gate before anything else happens. Nothing downstream (JD matching,
panel assignment) should run on a candidate you haven't cleared.

## Step 1 — run the deterministic timeline check first

Before reading qualitatively, extract the candidate's employment history into
a JSON file shaped like:

```json
{ "employment_history": [ { "company": "...", "title": "...", "start": "YYYY-MM", "end": "YYYY-MM or present" } ] }
```

Run it through the timeline tool:

```
python tools/verify_resume_dates.py <path-to-json>
```

The tool returns `overlaps` (two roles claimed at once), `gaps` (unexplained
months between roles), and `out_of_order` entries. Treat every reported
`overlap` as a blocker candidate (see severity table below) — don't re-derive
date math yourself, the tool is the source of truth for it.

## Step 2 — qualitative checks (you do these, not the tool)

| Check | What you're looking for | Severity if failed |
| --- | --- | --- |
| Timeline overlap (from tool) | Two concurrent full-time roles with no contracting/freelance explanation | blocker |
| Timeline gap (from tool) | Gap > 6 months with no narrative explanation anywhere in the resume | minor (gaps happen — only escalate if combined with other flags) |
| Education plausibility | Degree timeline must fit before the claimed start of full-time work; no claimed degree from an unaccredited or nonexistent-sounding institution presented as a named, ranked university | blocker |
| Skill corroboration | Every headline skill (e.g., "Kubernetes", "Spanish — fluent") must be supported by at least one role, project, or credential elsewhere in the resume. A skill listed with zero supporting evidence anywhere is a flag, not an automatic blocker | minor (blocker if 3+ uncorroborated headline skills) |
| Contact info format | Email matches a standard address shape; phone number matches a plausible national format | minor (blocker only if absent entirely) |
| Internal contradiction | Two different "current employers," conflicting seniority claims, or a title that contradicts the stated years of experience | blocker |

## Verdict

Exactly one blocker ⇒ `REJECTED`. Zero blockers ⇒ `LEGITIMATE`, regardless of
how many minor flags exist (list them anyway — JD matching may care).

Output format:

```
VERDICT: LEGITIMATE | REJECTED
FLAGS:
- [blocker|minor] <flag> — <one-line reason>
```

If `REJECTED`, stop there — do not produce a JD fit assessment or panel
recommendation. That is the coordinator's job to enforce, but you should never
volunteer downstream analysis on a rejected candidate.
