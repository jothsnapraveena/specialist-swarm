"""
Talent Cortex — Progress Tracker (shared contract between BACKEND and DASHBOARD).

The backend team imports this and calls `record_*` helpers as a drive moves
through the gated pipeline. It writes a single rolling file `data/progress.json`
that the Flight Deck dashboard reads (set `DATA_DIR=../data` on the dashboard, or
copy progress.json into dashboard/data.json for the demo).

This is the ONE file both teams agree on. Keep the field names identical to
`dashboard/data.json` so the dashboard renders without remapping.

Usage (backend side):

    from tracker.progress_tracker import Tracker
    tk = Tracker("data")                       # writes data/progress.json

    tk.upsert_position("pos_001", title="Senior Data Engineer",
                       location="Bengaluru", status="Open", openings=2,
                       must_have=["Python","Spark"], applicants=5)

    tk.upsert_candidate("cand_001", name="Ananya Rao", position="pos_001",
                        location="Bengaluru", skills=["Python","Spark"],
                        stage="Background Check")

    # as each gate resolves:
    tk.set_candidate_stage("cand_001", stage="JD Match",
                           bg_check="LEGITIMATE", jd_score=91)
    tk.set_candidate_result("cand_001", result="Selected", stage="Selected")

    tk.record_interview(candidate="Ananya Rao", position="Senior Data Engineer",
                        panel=["Dr. Suresh Kumar"], mode="In-Person",
                        datetime="2026-06-18 10:00", skill_overlap="4/4",
                        status="Scheduled", result="Pending")

No third-party deps — stdlib only, safe to vendor into the backend repo.
"""

import json
import os
from pathlib import Path

STAGES = [
    "Background Check", "JD Match", "Panel Matching",
    "Interviewing", "Selected", "Rejected",
]


class Tracker:
    def __init__(self, data_dir="data"):
        self.path = Path(data_dir) / "progress.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {
            "candidates": [], "open_positions": [], "panelists": [],
            "interviews": [],
            "pipeline_summary": {
                "background_check": 0, "jd_match": 0, "panel_match": 0,
                "interviewing": 0, "selected": 0, "rejected": 0,
            },
        }

    def _save(self):
        self._recount()
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _find(self, coll, _id):
        for x in self.state[coll]:
            if x.get("id") == _id:
                return x
        return None

    # ---- positions ----
    def upsert_position(self, pos_id, **fields):
        row = self._find("open_positions", pos_id)
        if row is None:
            row = {"id": pos_id}
            self.state["open_positions"].append(row)
        row.update(fields)
        self._save()

    # ---- candidates ----
    def upsert_candidate(self, cand_id, **fields):
        row = self._find("candidates", cand_id)
        if row is None:
            row = {"id": cand_id, "stage": "Background Check",
                   "bg_check": "RUNNING", "jd_score": None, "result": "Pending"}
            self.state["candidates"].append(row)
        row.update(fields)
        self._save()

    def set_candidate_stage(self, cand_id, **fields):
        self.upsert_candidate(cand_id, **fields)

    def set_candidate_result(self, cand_id, result, stage=None):
        f = {"result": result}
        if stage:
            f["stage"] = stage
        self.upsert_candidate(cand_id, **f)

    # ---- panelists ----
    def replace_panelists(self, pool):
        self.state["panelists"] = pool
        self._save()

    # ---- interviews ----
    def record_interview(self, **fields):
        fields.setdefault("scheduled_by", "Panelist Agent")
        self.state["interviews"].append(fields)
        self._save()

    # ---- derived ----
    def _recount(self):
        c = self.state["candidates"]
        s = self.state["pipeline_summary"]
        order = {st: i for i, st in enumerate(STAGES)}
        reached = lambda cand, st: order.get(cand.get("stage", ""), -1) >= order[st]
        s["background_check"] = sum(1 for x in c if x.get("bg_check") in ("LEGITIMATE", "REJECTED", "RUNNING"))
        s["jd_match"] = sum(1 for x in c if x.get("jd_score") is not None)
        s["panel_match"] = sum(1 for x in c if reached(x, "Panel Matching"))
        s["interviewing"] = sum(1 for x in c if x.get("stage") == "Interviewing")
        s["selected"] = sum(1 for x in c if str(x.get("result", "")).startswith("Selected"))
        s["rejected"] = sum(1 for x in c if str(x.get("result", "")).startswith("Rejected"))


if __name__ == "__main__":
    # smoke test: writes a tiny progress.json under ./data
    tk = Tracker(os.environ.get("DATA_DIR", "data"))
    tk.upsert_position("pos_001", title="Senior Data Engineer", location="Bengaluru",
                       status="Open", openings=2, must_have=["Python", "Spark"], applicants=1)
    tk.upsert_candidate("cand_001", name="Demo Candidate", position="pos_001",
                        location="Bengaluru", skills=["Python", "Spark"], stage="JD Match",
                        bg_check="LEGITIMATE", jd_score=88)
    print(f"Wrote {tk.path}")
