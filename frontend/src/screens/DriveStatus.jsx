import { useEffect, useState } from "react";
import { api } from "../api.js";

const TERMINAL = new Set(["REJECTED_BACKGROUND", "REJECTED_FIT", "COMPLETED", "FAILED"]);

function StageRow({ icon, name, detail }) {
  return (
    <div className="stage-row">
      <span className={`stage-icon ${icon.cls}`}>{icon.glyph}</span>
      <span className="stage-name">{name}</span>
      <span className="stage-detail">{detail}</span>
    </div>
  );
}

function iconFor(state) {
  switch (state) {
    case "pass": return { cls: "pass", glyph: "✓" };
    case "fail": return { cls: "fail", glyph: "✗" };
    case "running": return { cls: "running", glyph: "●" };
    default: return { cls: "pending", glyph: "○" };
  }
}

export default function DriveStatus({ driveId, onViewResults }) {
  const [drive, setDrive] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const data = await api.getDrive(driveId);
        if (cancelled) return;
        setDrive(data);
        if (!TERMINAL.has(data.status)) {
          timer = setTimeout(poll, 2500);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [driveId]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!drive) return <p>Loading drive…</p>;

  const bgState =
    drive.background_check?.verdict === "REJECTED" ? "fail" :
    drive.background_check?.verdict === "LEGITIMATE" ? "pass" :
    drive.status === "RUNNING_BACKGROUND_CHECK" ? "running" : "pending";

  const jdState =
    drive.jd_match?.recommendation === "REJECT" ? "fail" :
    drive.jd_match?.recommendation ? "pass" :
    drive.status === "RUNNING_JD_MATCH" ? "running" : "pending";

  const panelState =
    drive.status === "COMPLETED" && drive.panel_match ? "pass" :
    drive.status === "RUNNING_PANEL_MATCH" ? "running" : "pending";

  const isTerminal = TERMINAL.has(drive.status);

  return (
    <div>
      <h1>Drive Status</h1>
      <p className="subtitle">Drive {drive.drive_id}</p>

      {drive.status === "FAILED" && (
        <div className="error-banner">{drive.error}</div>
      )}

      <div className="card">
        <StageRow
          icon={iconFor(bgState)}
          name="Background Verification"
          detail={
            drive.background_check?.verdict
              ? drive.background_check.verdict
              : bgState === "running" ? "running…" : "pending"
          }
        />
        <StageRow
          icon={iconFor(jdState)}
          name="JD Match"
          detail={
            drive.jd_match?.recommendation
              ? drive.jd_match.recommendation
              : jdState === "running" ? "running…" : "pending"
          }
        />
        <StageRow
          icon={iconFor(panelState)}
          name="Panelist Matching"
          detail={
            panelState === "pass" ? "matched" :
            panelState === "running" ? "running…" : "pending"
          }
        />
      </div>

      {isTerminal && (
        <button className="primary" onClick={() => onViewResults(driveId)}>
          View Results
        </button>
      )}
    </div>
  );
}
