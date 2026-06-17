import { useEffect, useState } from "react";
import { api } from "../api.js";

const TERMINAL = new Set(["REJECTED_BACKGROUND", "REJECTED_FIT", "COMPLETED", "FAILED"]);

const ICONS = {
  pass: { cls: "pass", glyph: "✓" },
  fail: { cls: "fail", glyph: "✕" },
  running: { cls: "running", glyph: "" },
  pending: { cls: "", glyph: "" },
};

function Badge({ tone, children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function StageRow({ state, name, children }) {
  const icon = ICONS[state];
  return (
    <div className="stage-row">
      <span className={`stage-icon ${icon.cls}`}>{icon.glyph}</span>
      <div className="stage-body">
        <div className="stage-name">{name}</div>
        <div className="stage-detail">{children}</div>
      </div>
    </div>
  );
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

  if (error) return <div className="error-banner">⚠ {error}</div>;
  if (!drive) {
    return (
      <div className="loading-line">
        <span className="spinner" /> Loading drive…
      </div>
    );
  }

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
  const isRejected = drive.status === "REJECTED_BACKGROUND" || drive.status === "REJECTED_FIT";

  return (
    <div>
      <span className="eyebrow">● Stage 2 of 3</span>
      <h1>Drive Status</h1>
      <p className="subtitle mono">{drive.drive_id}</p>

      {drive.status === "FAILED" && <div className="error-banner">⚠ {drive.error}</div>}

      <div className="card">
        <div className="stepper">
          <StageRow state={bgState} name="Background Verification">
            {drive.background_check?.verdict ? (
              <Badge tone={drive.background_check.verdict === "LEGITIMATE" ? "green" : "red"}>
                {drive.background_check.verdict}
              </Badge>
            ) : bgState === "running" ? (
              <span><span className="spinner" />running…</span>
            ) : (
              "pending"
            )}
          </StageRow>

          <StageRow state={jdState} name="JD Match">
            {drive.jd_match?.recommendation ? (
              <Badge
                tone={
                  drive.jd_match.recommendation === "PROCEED" ? "green" :
                  drive.jd_match.recommendation === "HOLD" ? "amber" : "red"
                }
              >
                {drive.jd_match.recommendation}
              </Badge>
            ) : jdState === "running" ? (
              <span><span className="spinner" />running…</span>
            ) : (
              "pending"
            )}
          </StageRow>

          <StageRow state={panelState} name="Panelist Matching">
            {panelState === "pass" ? (
              <Badge tone="blue">matched</Badge>
            ) : panelState === "running" ? (
              <span><span className="spinner" />running…</span>
            ) : (
              "pending"
            )}
          </StageRow>
        </div>
      </div>

      {!isTerminal && (
        <p className="empty-state">
          {isRejected ? "" : "The drive is running — this updates automatically, no need to refresh."}
        </p>
      )}

      {isTerminal && (
        <button className="primary" onClick={() => onViewResults(driveId)}>
          View Results →
        </button>
      )}
    </div>
  );
}
