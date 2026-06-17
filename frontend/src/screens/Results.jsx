import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Results({ driveId }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getReport(driveId).then(setReport).catch((err) => setError(err.message));
  }, [driveId]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!report) return <p>Loading report…</p>;

  const verdict = report.background_check?.verdict;
  const recommendation = report.jd_match?.recommendation;

  return (
    <div>
      <h1>Interview Readiness Pack</h1>
      <p className="subtitle">Drive {report.drive_id} — status: {report.status}</p>

      <div className="card">
        <h2>Background Verification</h2>
        {verdict ? (
          <p>
            Verdict: <strong>{verdict}</strong>
          </p>
        ) : (
          <p className="empty-state">No background check result captured.</p>
        )}
        {report.background_check?.raw && <pre>{report.background_check.raw}</pre>}
      </div>

      {report.jd_match && (
        <div className="card">
          <h2>JD Fit</h2>
          <p>
            Recommendation: <strong>{recommendation}</strong>
          </p>
          <pre>{report.jd_match.raw}</pre>
        </div>
      )}

      {report.panel_match && (
        <div className="card">
          <h2>Recommended Panel</h2>
          <pre>{report.panel_match.raw}</pre>
        </div>
      )}

      <div className="card">
        <h2>Full Transcript</h2>
        <pre>{report.full_transcript}</pre>
      </div>
    </div>
  );
}
