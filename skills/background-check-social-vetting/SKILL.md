---
name: background-check-social-vetting
description: Recruitment background check skill combining resume verification (employment timeline, education/cert plausibility, skill corroboration, contact-info validity, internal contradictions) with social-media and open-source profile vetting (profile-vs-resume consistency, professional-conduct signals, identity corroboration, fabricated-credential signals). Use whenever vetting a candidate profile before interview — outputs LEGITIMATE or REJECTED with a structured flag list. Trigger on any request to background-check, verify a resume, vet a candidate, screen a profile, or check for resume fraud.
---

# Background Check & Social Vetting

This skill is applied by the **Background Verification Specialist**. It covers two lanes —
resume-internal verification and external (social/public profile) vetting — then produces a
single unified verdict.

## Verdict vocabulary

| Verdict | Meaning |
| --- | --- |
| `LEGITIMATE` | No blocker flags found; candidate may proceed to JD matching |
| `REJECTED` | One or more blocker flags found; pipeline stops here |

A **single blocker** is sufficient to produce `REJECTED`. Multiple minor flags do NOT
accumulate to a blocker; surface them for recruiter awareness only.

---

## Lane 1 — Resume / profile internal verification

Check the submitted text for the following, in order.

### 1.1 Employment timeline consistency

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Overlapping employment dates | Two roles with overlapping full-time periods and no explanation (e.g. not a side-project or consulting overlap) | Overlap ≤ 1 month (likely rounding) |
| Contradictory dates | Start date after end date for the same role | — |
| Current employer conflict | Two roles listed as "current" simultaneously | — |
| Unexplained gaps | Gap > 12 months with no narrative (career break, education, etc.) | Gap 6–12 months with no narrative |
| Date format inconsistency | Dates shift format in a way that conceals overlap (e.g. "2021" vs "Jan 2022") when the ambiguity produces a logical contradiction | Inconsistent formats alone, no logical contradiction |

### 1.2 Education and certification plausibility

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Impossible degree timeline | Degree completed before institution's founding date, or completion year precedes enrollment year | Enrollment year not stated (cannot verify) |
| Credential stack contradiction | Candidate claims a certification that requires a prerequisite credential that is absent | Certification year precedes typical experience requirement by >2 years |
| Degree/title mismatch | Role title claims PhD-level expertise (e.g. "Principal Research Scientist") but highest stated degree is high-school | High-degree role with no degree stated at all (treat as minor: degree not always required) |

### 1.3 Skill claim corroboration

Rule: every skill listed in the Skills section must be traceable to at least one supporting
signal elsewhere in the profile (job duties, project descriptions, tools mentioned in a role).

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Uncorroborated core skill | A must-have skill from the JD appears in the Skills section but has zero supporting evidence across all roles and projects | A nice-to-have or peripheral skill listed with no supporting evidence |
| Technology version anachronism | Skill listed with a version number that did not exist during the candidate's stated employment period (e.g. claiming Python 3.10 experience in a role that ended before Python 3.10 was released) | Version number omitted — cannot verify |

### 1.4 Contact information validity

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Malformed email | Email has no `@` or no TLD, or contains spaces | Unusual TLD (e.g. `.xyz`) |
| Malformed phone | Phone has fewer than 7 or more than 15 digits after stripping formatting | Phone uses non-standard country code prefix |
| No contact info at all | Neither email nor phone provided | Only one of email/phone provided |

### 1.5 Internal contradictions

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Conflicting employer name | Same role cited with two different company names in different sections | Minor abbreviation vs full-name inconsistency |
| Location contradiction | Profile states candidate is "based in London" but every role for the past 5 years lists "San Francisco office" with no remote flag | City vs country discrepancy without contradiction |
| Title contradiction | Job title in summary/headline contradicts title in employment history for the same role | Seniority label differs (e.g. "Senior" vs "Lead") |

---

## Lane 2 — Social media and open-source profile vetting

**Scope:** This is textual/heuristic analysis of publicly provided profile data or links
included in the submitted application. It is NOT real-time web scraping. If no public
profile data is provided, skip this lane and note "no public profile data supplied."

**Bias guardrail (mandatory):** Evaluate ONLY job-relevant signals. Do NOT flag, penalise,
or weight: age, gender, ethnicity, nationality, religion, political affiliation, disability,
family status, or any other protected characteristic. If a flag would implicitly encode a
protected characteristic, drop it.

### 2.1 Profile vs resume consistency

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Employer mismatch | LinkedIn/GitHub employer for a current role contradicts the resume employer name (not an abbreviation — a different company) | Profile employer is more specific/abbreviated vs resume |
| Title mismatch | Current job title on social profile differs materially from resume (different function, not just seniority label) | Seniority label differs |
| Education mismatch | Degree/institution on profile contradicts resume | Graduation year off by 1 year |
| Employment gap visible on profile | Profile shows a role omitted from the resume that, if included, would change the timeline verdict | Role on profile not on resume but irrelevant to timeline |

### 2.2 Professional conduct signals

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Publicly documented misconduct | Profile links to or references a verifiable public professional-conduct action (regulatory sanction, published misconduct finding) relevant to the role | Single ambiguous public complaint with no corroboration |
| Explicit policy-violating content | Open-source contributions or public posts that openly violate the employer's stated code of conduct (hate speech, harassment, IP theft attribution) — only if the content is unambiguous and job-relevant | — |

### 2.3 Identity and employer corroboration

| Check | Blocker condition | Minor condition |
| --- | --- | --- |
| Employer never existed | A stated employer has no verifiable public presence (website, press, LinkedIn company page, incorporation record) AND the role dates cannot be explained by a very early-stage startup | Employer is a very small / defunct company with limited public footprint |
| Fabricated credential signal | Certification body listed does not exist, OR the certificate number format contradicts the issuing body's documented format | Certificate number not provided (cannot verify) |

---

## Output format

```
VERDICT: <LEGITIMATE | REJECTED>

FLAGS:
  - severity: <blocker | minor | none>
    lane: <resume | social>
    check: <short check name, e.g. "Employment timeline overlap">
    detail: "<specific observation — quote or describe the exact text that triggered this flag>"
    why: "<which rule above applies>"

SUMMARY: <1-2 sentence plain-English summary of the decision>
```

If no flags exist, output `FLAGS: none` and `VERDICT: LEGITIMATE`.

### Example flag block

```
FLAGS:
  - severity: blocker
    lane: resume
    check: Current employer conflict
    detail: "Role 2 (Acme Corp, 2021–present) and Role 4 (Beta Ltd, 2022–present) are both listed as current."
    why: "1.5 Internal contradictions — two roles listed as 'current' simultaneously."

  - severity: minor
    lane: social
    check: Seniority label differs
    detail: "LinkedIn shows 'Software Engineer'; resume shows 'Senior Software Engineer' for the same role."
    why: "2.1 Profile vs resume consistency — seniority label differs (minor)."

VERDICT: REJECTED
SUMMARY: One blocker flag found — two simultaneous 'current' employers listed, indicating an internal contradiction. Minor social-profile discrepancy noted for recruiter awareness.
```
