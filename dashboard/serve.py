"""
Talent Cortex — Flight Deck dashboard server (Python stdlib only).

Serves the dashboard UI and a /api/state endpoint that merges:
  - dashboard/agent_status.json  (the agent fleet + tasks, with REAL token usage
    recorded by the orchestrator from each subagent's reported usage)
  - dashboard/data.json          (DUMMY recruitment data until the data teammate
    pushes real synthetic data into a branch)
and computes the cost / ROI optimization with a transparent, on-screen formula.

No third-party deps. Run:
    python dashboard/serve.py            # serves on http://localhost:8765
    PORT=9000 python dashboard/serve.py  # custom port
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8765"))


def load_json(name):
    p = HERE / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


BACKEND_DATA = os.environ.get("BACKEND_DATA") or str(HERE.parent / "backend" / "data")

_STAGE = {
    "PENDING": "Background Check",
    "RUNNING_BACKGROUND_CHECK": "Background Check",
    "REJECTED_BACKGROUND": "Rejected",
    "RUNNING_JD_MATCH": "JD Match",
    "REJECTED_FIT": "Rejected",
    "HOLD_FIT": "JD Match",
    "RUNNING_PANEL_MATCH": "Panel Matching",
    "COMPLETED": "Interviewing",
    "FAILED": "Rejected",
}
_RESULT = {
    "REJECTED_BACKGROUND": "Rejected (Background)",
    "REJECTED_FIT": "Rejected (Fit)",
    "FAILED": "Rejected (Failed)",
    "COMPLETED": "Pending",
}


def _read(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None
    except (ValueError, OSError):
        return None


def _first_line(text, default=""):
    for ln in (text or "").splitlines():
        s = ln.strip().lstrip("#").strip()
        if s:
            return s[:80]
    return default


def _candidate_name(backend, cand_id):
    rec = _read(Path(backend) / "candidates" / (cand_id + ".json"))
    if not rec:
        return cand_id
    txt = rec.get("text", "")
    for ln in txt.splitlines():
        s = ln.strip()
        if s.lower().startswith("name"):
            nm = s.split(":", 1)[-1].strip()
            return (nm or cand_id)[:60]
    return _first_line(txt, cand_id)


def build_from_backend(backend):
    """Map the backend's native flat-JSON store (backend/data/) into the
    dashboard display shape. Returns None if there are no drives yet."""
    backend = Path(backend)
    drives_dir = backend / "drives"
    if not drives_dir.exists():
        return None
    status_files = sorted(drives_dir.glob("*/status.json"))
    if not status_files:
        return None

    pan_doc = _read(backend / "panelists.json") or {}
    pool = pan_doc.get("panelist_pool", []) if isinstance(pan_doc, dict) else (pan_doc or [])
    panelists = []
    for p in pool:
        avail = []
        for a in p.get("availability", []):
            slots = a.get("slots")
            slots = [str(slots) + " slot(s)"] if isinstance(slots, int) else (slots or [])
            avail.append({"date": a.get("date"), "slots": slots})
        panelists.append({"id": p.get("id"), "name": p.get("name"), "title": "Panelist",
                          "location": p.get("location", ""), "skills": p.get("skills", []),
                          "availability": avail})

    candidates, interviews = [], []
    summary = {"background_check": 0, "jd_match": 0, "panel_match": 0,
               "interviewing": 0, "selected": 0, "rejected": 0}
    job_applicants = {}

    for sf in status_files:
        st = _read(sf) or {}
        status = st.get("status", "PENDING")
        cand_id = st.get("candidate_id", "?")
        job_id = st.get("job_id")
        bg = (st.get("background_check") or {}).get("verdict")
        jd = (st.get("jd_match") or {}).get("recommendation")
        candidates.append({
            "id": cand_id, "name": _candidate_name(backend, cand_id),
            "position": job_id, "location": "", "skills": [],
            "stage": _STAGE.get(status, "Background Check"),
            "bg_check": bg or ("RUNNING" if status in ("PENDING", "RUNNING_BACKGROUND_CHECK") else "—"),
            "jd_score": None, "result": _RESULT.get(status, "Pending"),
        })
        if bg or status != "PENDING":
            summary["background_check"] += 1
        if jd or status in ("RUNNING_PANEL_MATCH", "COMPLETED"):
            summary["jd_match"] += 1
        if status in ("RUNNING_PANEL_MATCH", "COMPLETED"):
            summary["panel_match"] += 1
        if status == "COMPLETED":
            summary["interviewing"] += 1
            interviews.append({"candidate": _candidate_name(backend, cand_id),
                               "position": job_id or "—", "panel": ["(see readiness pack)"],
                               "mode": "—", "datetime": "—", "skill_overlap": "—",
                               "status": "Completed", "result": "Pending",
                               "scheduled_by": "Panelist Agent"})
        if str(status).startswith("REJECTED") or status == "FAILED":
            summary["rejected"] += 1
        if job_id:
            job_applicants[job_id] = job_applicants.get(job_id, 0) + 1

    positions = []
    jobs_dir = backend / "jobs"
    if jobs_dir.exists():
        for jf in sorted(jobs_dir.glob("*.json")):
            j = _read(jf) or {}
            jid = j.get("id", jf.stem)
            positions.append({"id": jid, "title": _first_line(j.get("text"), jid),
                              "location": "", "status": "Open", "openings": 1,
                              "must_have": [], "nice_to_have": [],
                              "applicants": job_applicants.get(jid, 0)})

    return {"_source": str(drives_dir), "candidates": candidates,
            "open_positions": positions, "panelists": panelists,
            "interviews": interviews, "pipeline_summary": summary}


def load_data():
    """Recruitment data for the dashboard, in priority order:
    1. Live from the backend's native store (backend/data/) via build_from_backend
    2. A progress.json written by the Tracker (DATA_DIR seam)
    3. The bundled dummy dashboard/data.json
    """
    backend = build_from_backend(BACKEND_DATA)
    if backend:
        return backend

    data_dir = os.environ.get("DATA_DIR")
    if data_dir:
        p = Path(data_dir) / "progress.json"
        if p.exists():
            try:
                live = json.loads(p.read_text(encoding="utf-8"))
                live.setdefault("_source", str(p))
                return live
            except (ValueError, OSError):
                pass
    return load_json("data.json")


DOC_CATEGORIES = [
    ("Product", ["PRD", "TECHNICAL-DESIGN", "TECH-DESIGN", "TEST-CASE", "TESTCASES"]),
    ("Specs", ["REQUIREMENTS"]),
    ("Design", ["architecture", "backend", "frontend", "scenario-cards"]),
    ("Guides", ["README", "CLAUDE", "stretch-goals"]),
]


def categorize(stem):
    for cat, keys in DOC_CATEGORIES:
        if any(k.lower() in stem.lower() for k in keys):
            return cat
    return "Other"


def load_docs():
    """Project Hub: collect markdown docs from the repo root and docs/ (not meetings)."""
    root = HERE.parent
    seen, out = set(), []
    candidates = sorted(root.glob("*.md")) + sorted((root / "docs").glob("*.md"))
    for f in candidates:
        if not f.is_file() or f.name in seen:
            continue
        seen.add(f.name)
        text = f.read_text(encoding="utf-8")
        first = next((ln for ln in text.splitlines() if ln.strip()), f.stem)
        out.append({
            "file": f.name,
            "title": first.lstrip("# ").strip(),
            "category": categorize(f.stem),
            "content": text,
        })
    return out


def load_live_agents():
    """Live backend agent activity written by tracker.record_agent -> agents.json."""
    data_dir = os.environ.get("DATA_DIR")
    if not data_dir:
        return []
    p = Path(data_dir) / "agents.json"
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return list(d.values()) if isinstance(d, dict) else d
    except (ValueError, OSError):
        return []


def load_meetings():
    """Read cross-team meeting records from <repo>/docs/meetings/*.md."""
    mdir = HERE.parent / "docs" / "meetings"
    if not mdir.exists():
        return []
    out = []
    for f in sorted(mdir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        first = next((ln for ln in text.splitlines() if ln.strip()), f.stem)
        out.append({
            "file": f.name,
            "title": first.lstrip("# ").strip(),
            "content": text,
        })
    return out


def compute_optimization(status):
    """Real tokens from agent_status.json -> blended cost vs a transparent human baseline."""
    pricing = status.get("pricing_blended", {})
    baseline = status.get("human_baseline", {})
    rate = baseline.get("rate_usd_per_hour", 100)

    total_tokens = 0
    ai_cost = 0.0
    human_hours = 0.0
    for a in status.get("agents", []):
        tokens = a.get("tokens", 0) or 0
        total_tokens += tokens
        human_hours += a.get("human_hours", 0) or 0
        rates = pricing.get(a.get("model", ""), {"in": 3, "out": 15})
        # blended: 70% input / 30% output
        cost = tokens * (0.7 * rates["in"] + 0.3 * rates["out"]) / 1_000_000
        a["cost_usd"] = round(cost, 4)
        ai_cost += cost

    human_cost = human_hours * rate
    savings = human_cost - ai_cost
    roi = round(savings / ai_cost, 1) if ai_cost > 0 else 0

    formula = (
        "AI cost  = Σ tokens × (0.7 × in_rate + 0.3 × out_rate) / 1e6\n"
        "           (70% input / 30% output assumption; published USD per 1M tokens)\n"
        f"Human    = {human_hours:.0f} hrs × ${rate}/hr = ${human_cost:,.0f}\n"
        f"Savings  = human − AI = ${savings:,.2f}\n"
        f"ROI      = savings / AI cost = {roi}×\n"
        "Tokens are ACTUAL subagent usage recorded by the orchestrator; human hours "
        "are a labelled estimate of manual build effort."
    )
    return {
        "total_tokens": total_tokens,
        "ai_cost_usd": round(ai_cost, 2),
        "human_cost_usd": round(human_cost, 2),
        "human_hours": round(human_hours),
        "rate": rate,
        "savings_usd": round(savings, 2),
        "roi_x": roi,
        "formula": formula,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            status = load_json("agent_status.json")
            data = load_data()
            opt = compute_optimization(status)

            # Overlay live backend agent activity onto the static team roster
            live_agents = load_live_agents()
            teams = status.get("teams", [])
            if live_agents:
                by_name = {a.get("name"): a for a in live_agents}
                for t in teams:
                    for m in t.get("members", []):
                        la = by_name.get(m.get("name"))
                        if la:
                            m["status"] = la.get("status", m["status"])
                            if la.get("tokens"):
                                m["tokens"] = la["tokens"]
                            if la.get("task"):
                                m["task"] = la["task"]
            state = {
                "product": status.get("product", "Talent Cortex"),
                "updated_at": status.get("updated_at"),
                "agents": status.get("agents", []),
                "teams": teams,
                "integration": status.get("integration", {}),
                "live_agents": live_agents,
                "tasks": status.get("tasks", []),
                "docs": load_docs(),
                "meetings": load_meetings(),
                "data": data,
                "optimization": opt,
            }
            return self._send(200, json.dumps(state))

        if self.path in ("/", "/index.html"):
            html = (HERE / "index.html").read_text(encoding="utf-8")
            return self._send(200, html, "text/html; charset=utf-8")

        # static fallthrough for any other dashboard asset
        rel = self.path.lstrip("/").split("?")[0]
        f = HERE / rel
        if f.exists() and f.is_file():
            ctypes = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json",
                ".svg": "image/svg+xml",
            }
            ctype = ctypes.get(f.suffix, "text/plain; charset=utf-8")
            return self._send(200, f.read_text(encoding="utf-8"), ctype)

        self._send(404, json.dumps({"error": "not found"}))


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Talent Cortex Flight Deck -> http://localhost:{PORT}")
    print("Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
