"""
Deterministic employment-timeline check, called by the Background
Verification Specialist (skills/resume-verification-checklist) via the bash
tool. Date math is exactly the kind of thing a model should not eyeball.

Input: a JSON file shaped like
    { "employment_history": [
        { "company": "...", "title": "...", "start": "YYYY-MM", "end": "YYYY-MM" or "present" }
    ] }

Output (printed as JSON to stdout):
    { "overlaps": [...], "gaps": [...], "out_of_order": [...] }

Usage:
    python tools/verify_resume_dates.py <path-to-profile.json>
"""

import json
import sys
from datetime import date


def parse_month(value: str) -> date:
    if value.strip().lower() == "present":
        return date.today()
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/verify_resume_dates.py <path-to-profile.json>")

    data = json.loads(open(sys.argv[1]).read())
    history = data.get("employment_history", [])

    parsed = []
    for entry in history:
        start = parse_month(entry["start"])
        end = parse_month(entry["end"])
        parsed.append({**entry, "_start": start, "_end": end})

    parsed.sort(key=lambda e: e["_start"])

    overlaps = []
    gaps = []
    out_of_order = []

    for entry in parsed:
        if entry["_end"] < entry["_start"]:
            out_of_order.append(
                {"company": entry["company"], "title": entry["title"],
                 "reason": f"end {entry['end']} is before start {entry['start']}"}
            )

    for prev, cur in zip(parsed, parsed[1:]):
        if cur["_start"] < prev["_end"]:
            overlaps.append({
                "first": f"{prev['title']} @ {prev['company']} ({prev['start']}–{prev['end']})",
                "second": f"{cur['title']} @ {cur['company']} ({cur['start']}–{cur['end']})",
            })
        else:
            gap_months = (cur["_start"].year - prev["_end"].year) * 12 + (cur["_start"].month - prev["_end"].month)
            if gap_months > 6:
                gaps.append({
                    "between": f"{prev['title']} @ {prev['company']}",
                    "and": f"{cur['title']} @ {cur['company']}",
                    "gap_months": gap_months,
                })

    print(json.dumps({
        "overlaps": overlaps,
        "gaps": gaps,
        "out_of_order": out_of_order,
    }, indent=2))


if __name__ == "__main__":
    main()
