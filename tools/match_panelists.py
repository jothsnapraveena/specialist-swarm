"""
Deterministic panelist matching, called by the Panelist Matching Specialist
(skills/panelist-matching-policy) via the bash tool. Implements the fixed
decision order from the skill exactly: skill overlap (primary) -> availability
(secondary) -> location-based mode (per panelist). This is rule-based
computation, not judgment, so it lives in a tool rather than being left to
the model to eyeball against a JSON blob.

Input: a JSON file shaped like
    {
      "candidate_location": "...",
      "required_skills": ["...", "..."],
      "interview_date": "YYYY-MM-DD",
      "panelist_pool": [
        { "id": "...", "name": "...", "skills": ["..."], "location": "...",
          "availability": [ { "date": "YYYY-MM-DD", "slots": 1 } ] }
      ]
    }

Output (printed as JSON to stdout): ranked slate, or an empty list with the
closest-miss explanation if nobody clears both criteria.

Usage:
    python tools/match_panelists.py <path-to-input.json>
"""

import json
import sys

TOP_N = 3


def skill_overlap(panelist_skills: list[str], required_skills: list[str]) -> tuple[int, int]:
    panelist_set = {s.lower() for s in panelist_skills}
    required_set = {s.lower() for s in required_skills}
    overlap = panelist_set & required_set
    return len(overlap), len(required_set)


def availability_on(panelist: dict, interview_date: str) -> dict | None:
    for slot in panelist.get("availability", []):
        if slot["date"] == interview_date and slot.get("slots", 0) > 0:
            return slot
    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/match_panelists.py <path-to-input.json>")

    data = json.loads(open(sys.argv[1]).read())
    candidate_location = data["candidate_location"]
    required_skills = data["required_skills"]
    interview_date = data["interview_date"]
    pool = data["panelist_pool"]

    # 1. Skill match (primary) — rank, exclude zero overlap.
    ranked = []
    for panelist in pool:
        overlap_count, total = skill_overlap(panelist["skills"], required_skills)
        if overlap_count == 0:
            continue
        ranked.append((overlap_count, total, panelist))
    ranked.sort(key=lambda r: r[0], reverse=True)

    # 2. Availability (secondary) — filter the skill-ranked list, never reorder by it.
    slate = []
    closest_miss = None
    for overlap_count, total, panelist in ranked:
        slot = availability_on(panelist, interview_date)
        if slot is None:
            if closest_miss is None:
                closest_miss = (
                    f"{panelist['name']} has {overlap_count}/{total} skill overlap "
                    f"but no availability on {interview_date}"
                )
            continue

        # 3. Mode — per panelist, by location match.
        mode = "In-Person" if panelist["location"] == candidate_location else "Online"
        reason = (
            f"same location ({candidate_location})" if mode == "In-Person"
            else f"candidate in {candidate_location}, panelist in {panelist['location']}"
        )
        slate.append({
            "id": panelist["id"],
            "name": panelist["name"],
            "skill_overlap": f"{overlap_count}/{total}",
            "skill_overlap_pct": round(100 * overlap_count / total) if total else 0,
            "availability_used": slot["date"],
            "mode": mode,
            "mode_reason": reason,
        })
        if len(slate) >= TOP_N:
            break

    print(json.dumps({
        "slate": slate,
        "closest_miss": closest_miss if not slate else None,
    }, indent=2))


if __name__ == "__main__":
    main()
