import { useState, useEffect } from 'react';
import { getDriveReport, openDriveReportDownload } from '../api';
import StageRow from './StageRow';

const MET_LABEL = { met: 'Met', partial: 'Partial', missing: 'Missing' };
const MET_CLASS = { met: 'met', partial: 'partial', missing: 'missing' };

export default function ReadinessPack({ driveId, onBack, onNewDrive }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDriveReport(driveId)
      .then(setReport)
      .catch((err) => setError(err.message));
  }, [driveId]);

  if (error) {
    return (
      <div className="screen">
        <div className="error-banner">{error}</div>
        <button className="btn-secondary" onClick={onBack}>Back to Drive Status</button>
      </div>
    );
  }

  if (!report) {
    return <div className="screen"><div className="loading">Loading report…</div></div>;
  }

  const bg = report.background_check || {};
  const jd = report.jd_match || {};
  const panel = report.panel_match || {};
  const slate = panel.panel_slate || [];
  const mustHave = jd.must_have || [];
  const niceToHave = jd.nice_to_have || [];

  const isLegitimate = bg.verdict === 'LEGITIMATE';

  return (
    <div className="screen">
      <div className="drive-header">
        <div>
          <h2>Interview Readiness Pack</h2>
          <span className="drive-id">Drive ID: {driveId}</span>
        </div>
        <button className="btn-export" onClick={() => openDriveReportDownload(driveId)}>
          ↓ Export (DOCX)
        </button>
      </div>

      {/* Verdict Banner */}
      <div className={`verdict-banner ${isLegitimate ? 'verdict-pass' : 'verdict-fail'}`}>
        <span className="verdict-icon">{isLegitimate ? '✓' : '✗'}</span>
        <div>
          <div className="verdict-label">Background Check: {bg.verdict}</div>
          {jd.score !== undefined && (
            <div className="verdict-score">JD Fit Score: <strong>{jd.score}/100</strong></div>
          )}
        </div>
      </div>

      {/* Stage Summary (compact) */}
      <div className="stages-card compact">
        <StageRow name="Background Verification" status="passed" summary={bg.verdict} />
        <StageRow
          name="JD Match"
          status="passed"
          summary={jd.recommendation ? `Score ${jd.score} — ${jd.recommendation}` : `Score ${jd.score}`}
        />
        <StageRow
          name="Panelist Matching"
          status="passed"
          summary={slate.length ? `${slate.length} panelist${slate.length !== 1 ? 's' : ''} selected` : 'No panelist cleared both criteria'}
        />
      </div>

      {/* JD Fit Table */}
      {(mustHave.length > 0 || niceToHave.length > 0) && (
        <div className="report-card">
          <h3>JD Fit Breakdown</h3>
          <table className="report-table">
            <thead>
              <tr>
                <th>Skill</th>
                <th>Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {mustHave.map((s, i) => (
                <tr key={`must-${i}`}>
                  <td>{s.skill}</td>
                  <td><span className="tag tag-must">Must-have</span></td>
                  <td>
                    <span className={`status-chip ${MET_CLASS[s.status] || ''}`}>
                      {MET_LABEL[s.status] || s.status}
                    </span>
                  </td>
                </tr>
              ))}
              {niceToHave.map((s, i) => (
                <tr key={`nice-${i}`}>
                  <td>{s.skill}</td>
                  <td><span className="tag tag-nice">Nice-to-have</span></td>
                  <td>
                    <span className={`status-chip ${MET_CLASS[s.status] || ''}`}>
                      {MET_LABEL[s.status] || s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Panel Slate */}
      <div className="report-card">
        <h3>Recommended Interview Panel</h3>
        {slate.length === 0 ? (
          <div className="empty-state">
            No panelist cleared both skill overlap and availability criteria.
            Consider updating the panelist pool or interview window.
          </div>
        ) : (
          <table className="report-table">
            <thead>
              <tr>
                <th>Panelist</th>
                <th>Skill Overlap</th>
                <th>Availability</th>
                <th>Mode</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {slate.map((p, i) => (
                <tr key={i}>
                  <td><strong>{p.name}</strong></td>
                  <td>{p.skill_overlap}</td>
                  <td>{p.availability_slot}</td>
                  <td>
                    <span className={`mode-chip ${p.mode === 'In-Person' ? 'in-person' : 'online'}`}>
                      {p.mode}
                    </span>
                  </td>
                  <td className="why-cell">{p.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="drive-actions">
        <button className="btn-secondary" onClick={onBack}>← Back to Drive Status</button>
        <button className="btn-primary" onClick={onNewDrive}>Start New Drive</button>
      </div>
    </div>
  );
}
