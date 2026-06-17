---
name: resume-verification-checklist
description: Background-check checklist for validating whether a candidate resume/profile is genuine before any JD matching happens. Use whenever asked to verify, validate, or background-check a candidate resume or profile. Trigger on any request to confirm a resume is legitimate, flag inconsistencies, or decide whether a candidate should proceed past intake.
---

# Resume Verification Checklist

You are the gate before anything else happens. Nothing downstream (JD matching,
panel assignment) should run on a candidate you haven't cleared.

**The only question that matters here is genuineness: is this a real person
with a real employment history, not a fabricated or impersonated profile?**
This is not a resume-quality review — gaps, thin sections, and formatting
issues are not what this check exists to catch. Don't reject a candidate for
being imperfect; reject only for credible signs the profile isn't real.

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
months between roles), and `out_of_order` entries. Don't re-derive date math
yourself — the tool is the source of truth for it. **Gaps are never a
rejection reason on their own, no matter how long** — only `overlaps` feed
into the blocker rules below.

## Step 2 — verify LinkedIn presence via web search

Use the web search tool (part of your toolset) to confirm this is a real,
findable person — this is the primary genuineness signal:

- If the resume includes an explicit LinkedIn URL, fetch it directly.
  Otherwise, search for `"<candidate name>" "<most recent employer>" linkedin`
  and look for a profile that plausibly belongs to this candidate.
- **Profile found and consistent** (current employer/title roughly match the
  resume, allowing for minor wording differences): no flag.
- **Profile found but contradicts the resume** (different current employer,
  different title, employment dates that don't reconcile): blocker.
- **No matching profile can be found at all**: blocker. A real candidate
  should be findable; treat this as a genuineness failure, not a minor
  formatting gap.
- Note what you searched for and what you found (or didn't) in your flags
  list so the coordinator can see the check was actually performed.

## Step 3 — other checks (informational only — none of these reject)

These are worth surfacing to the hiring manager, but **must never affect the
verdict**. List them as `minor` flags if present; never escalate them to
`blocker` regardless of how many accumulate.

| Check | What you're looking for |
| --- | --- |
| Timeline gap (from tool) | Any gap between roles, of any length |
| Education detail | Thin, missing, or unusually-phrased education section |
| Skill corroboration | A headline skill with no supporting evidence elsewhere in the resume |
| Contact info format | Missing or oddly-formatted email/phone |

## Blocker conditions (the only things that can reject a candidate)

| Check | What you're looking for |
| --- | --- |
| LinkedIn not found | Step 2 found no plausible profile for this candidate |
| LinkedIn contradiction | Step 2 found a profile, but it contradicts the resume's employer/title/dates |
| Timeline overlap (from tool) | Two concurrent full-time roles claimed with no contracting/freelance explanation — signals a fabricated timeline |
| Internal self-contradiction | The resume itself states two different "current employers," or a title that's flatly inconsistent with itself |

## Verdict

Exactly one blocker ⇒ `REJECTED`. Zero blockers ⇒ `LEGITIMATE` — regardless
of how many Step 3 informational flags exist (list them anyway; JD matching
or the hiring manager may care, but they never drive the verdict).

Output format:

```
VERDICT: LEGITIMATE | REJECTED
FLAGS:
- [blocker] <flag> — <one-line reason>          (only from the blocker table above)
- [minor] <flag> — <one-line reason>             (informational only, from Step 3)
```

If `REJECTED`, stop there — do not produce a JD fit assessment or panel
recommendation. That is the coordinator's job to enforce, but you should never
volunteer downstream analysis on a rejected candidate.
