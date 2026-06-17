import { useEffect, useState } from "react";
import { api } from "../api.js";

function Badge({ tone, children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export default function Results({ driveId }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getReport(driveId).then(setReport).catch((err) => setError(err.message));
  }, [driveId]);

  if (error) return <div className="error-banner">⚠ {error}</div>;
  if (!report) {
    return (
      <div className="loading-line">
        <span className="spinner" /> Loading report…
      </div>
    );
  }

  const verdict = report.background_check?.verdict;
  const recommendation = report.jd_match?.recommendation;
  const rejected = report.status === "REJECTED_BACKGROUND" || report.status === "REJECTED_FIT";

  return (
    <div>
      <span className="eyebrow">● Stage 3 of 3</span>
      <h1>Interview Readiness Pack</h1>
      <p className="subtitle mono">{report.drive_id}</p>

      <div className={`verdict-banner ${rejected ? "bad" : "ok"}`}>
        <span className="icon">{rejected ? "✕" : "✓"}</span>
        <div>
          <div className="title">{report.status.replaceAll("_", " ")}</div>
          <div className="desc">
            {rejected
              ? "This drive stopped early — see the stage detail below for why."
              : "This drive reached the end of the gated pipeline."}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>🛡 Background Verification</h2>
        {verdict ? (
          <p>
            <Badge tone={verdict === "LEGITIMATE" ? "green" : "red"}>{verdict}</Badge>
          </p>
        ) : (
          <p className="empty-state">No background check result captured.</p>
        )}
        {report.background_check?.raw && (
          <details>
            <summary>Full specialist reply</summary>
            <pre>{report.background_check.raw}</pre>
          </details>
        )}
      </div>

      {report.jd_match && (
        <div className="card">
          <h2>🎯 JD Fit</h2>
          <p>
            <Badge
              tone={
                recommendation === "PROCEED" ? "green" :
                recommendation === "HOLD" ? "amber" : "red"
              }
            >
              {recommendation}
            </Badge>
          </p>
          <details>
            <summary>Full specialist reply</summary>
            <pre>{report.jd_match.raw}</pre>
          </details>
        </div>
      )}

      {report.panel_match && (
        <div className="card">
          <h2>👥 Recommended Panel</h2>
          <pre>{report.panel_match.raw}</pre>
        </div>
      )}

      <div className="card">
        <h2>📄 Full Transcript</h2>
        <details>
          <summary>Show coordinator's full synthesis</summary>
          <pre>{report.full_transcript}</pre>
        </details>
      </div>
    </div>
  );
}
