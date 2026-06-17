---
name: panelist-matching-policy
description: Fixed decision policy for matching interview panelists to a candidate — skill overlap first, availability second, then in-person/online mode by location. Use whenever asked to recommend an interview panel, match panelists to a candidate, or decide whether an interview should be in-person or online. Trigger on any request to assign, rank, or recommend panelists for a candidate.
---

# Panelist Matching Policy

This is a fixed decision order. Do not reorder it and do not relax an earlier
criterion to satisfy a later one.

1. **Skill match (primary).** Rank panelists by overlap between the
   panelist's skills and `REQUIRED_SKILLS_FOR_PANEL` from the JD Matching
   Specialist. A panelist with zero overlap is excluded outright, no matter
   how available they are.
2. **Availability (secondary).** Among the skill-ranked panelists, keep only
   those with an open slot in the interview window. If the top skill-ranked
   panelist has no availability, move to the next-ranked panelist — never go
   back and loosen the skill criterion to fill a slot.
3. **Mode (per panelist, not per slate).** For each selected panelist:
   `candidate.location == panelist.location` → `In-Person`. Otherwise →
   `Online`. A single panel can be mixed-mode; don't force uniformity.

## Run the deterministic tool — don't hand-compute this

Build the input JSON:

```json
{
  "candidate_location": "...",
  "required_skills": ["...", "..."],
  "interview_date": "YYYY-MM-DD",
  "panelist_pool": [ { "id": "...", "name": "...", "skills": ["..."], "location": "...", "availability": [ { "date": "YYYY-MM-DD", "slots": 1 } ] } ]
}
```

Then run:

```
python tools/match_panelists.py <path-to-input-json>
```

It returns a ranked slate with `skill_overlap_pct`, the availability slot
used, and the assigned `mode` per panelist — already computed per the order
above. Your job is to narrate and justify this output, not to recompute it by
eye. If the tool returns an empty slate, say so plainly:

```
NO PANELIST CLEARED BOTH CRITERIA.
<one line on the closest miss — e.g. "A. Rao has full skill overlap but no
availability in the window; no other panelist has more than 1/4 skill
overlap.">
```

Never force a weak match to fill a panel — an honest "no match" is more
useful than a bad one.

## Output format (non-empty slate)

```
PANEL:
- <name> — skill_overlap <n>/<total> — available <date> — mode: In-Person|Online (<reason>)
```
