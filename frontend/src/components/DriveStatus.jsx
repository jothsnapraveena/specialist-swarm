import { useState, useEffect, useRef } from 'react';
import { getDrive } from '../api';
import StageRow from './StageRow';

const TERMINAL = new Set([
  'REJECTED_BACKGROUND',
  'REJECTED_FIT',
  'HOLD_FIT',
  'COMPLETED',
  'FAILED',
]);

function deriveStages(drive) {
  const s = drive.status;

  const bgStatus = (() => {
    if (!s || s === 'PENDING') return 'pending';
    if (s === 'RUNNING_BACKGROUND_CHECK') return 'running';
    if (s === 'REJECTED_BACKGROUND') return 'rejected';
    return 'passed';
  })();

  const jdStatus = (() => {
    if (['PENDING', 'RUNNING_BACKGROUND_CHECK', 'REJECTED_BACKGROUND'].includes(s)) return 'pending';
    if (s === 'RUNNING_JD_MATCH') return 'running';
    if (s === 'REJECTED_FIT') return 'rejected';
    if (s === 'HOLD_FIT') return 'hold';
    return 'passed';
  })();

  const panelStatus = (() => {
    if (!['RUNNING_PANEL_MATCH', 'COMPLETED', 'FAILED'].includes(s)) return 'pending';
    if (s === 'RUNNING_PANEL_MATCH') return 'running';
    if (s === 'FAILED') return 'rejected';
    return 'passed';
  })();

  return { bgStatus, jdStatus, panelStatus };
}

function bgSummary(drive) {
  const bg = drive.background_check;
  if (!bg) return null;
  const flagCount = (bg.flags || []).filter((f) => f.severity === 'blocker').length;
  if (bg.verdict === 'REJECTED') return `REJECTED — ${flagCount} blocker flag${flagCount !== 1 ? 's' : ''}`;
  return bg.verdict;
}

function jdSummary(drive) {
  const jd = drive.jd_match;
  if (!jd) return null;
  if (jd.recommendation === 'PROCEED') return `Score ${jd.score} — PROCEED`;
  if (jd.recommendation === 'HOLD') return `Score ${jd.score} — HOLD`;
  return `Score ${jd.score} — REJECT`;
}

function panelSummary(drive) {
  const pm = drive.panel_match;
  if (!pm) return null;
  const count = (pm.panel_slate || []).length;
  if (count === 0) return 'No panelist cleared both criteria';
  return `${count} panelist${count !== 1 ? 's' : ''} selected`;
}

export default function DriveStatus({ driveId, onViewPack, onNewDrive }) {
  const [drive, setDrive] = useState(null);
  const [error, setError] = useState('');
  const intervalRef = useRef(null);

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const data = await getDrive(driveId);
        if (!active) return;
        setDrive(data);
        if (TERMINAL.has(data.status)) {
          clearInterval(intervalRef.current);
        }
      } catch (err) {
        if (!active) return;
        setError(err.message);
        clearInterval(intervalRef.current);
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 2500);

    return () => {
      active = false;
      clearInterval(intervalRef.current);
    };
  }, [driveId]);

  if (error) {
    return (
      <div className="screen">
        <div className="error-banner">{error}</div>
        <button className="btn-primary" onClick={onNewDrive}>Start New Drive</button>
      </div>
    );
  }

  if (!drive) {
    return (
      <div className="screen">
        <div className="loading">Loading drive status…</div>
      </div>
    );
  }

  const { bgStatus, jdStatus, panelStatus } = deriveStages(drive);
  const bgFlags = drive.background_check?.flags || [];
  const isTerminal = TERMINAL.has(drive.status);
  const isCompleted = drive.status === 'COMPLETED';
  const isFailed = drive.status === 'FAILED';

  return (
    <div className="screen">
      <div className="drive-header">
        <div>
          <h2>Drive Status</h2>
          <span className="drive-id">ID: {driveId}</span>
        </div>
        {!isTerminal && <span className="pulse-dot" />}
      </div>

      <div className="stages-card">
        <StageRow
          name="Background Verification"
          status={bgStatus}
          summary={bgSummary(drive)}
          flags={bgStatus === 'rejected' ? bgFlags : []}
        />
        <StageRow
          name="JD Match"
          status={jdStatus}
          summary={jdSummary(drive)}
        />
        <StageRow
          name="Panelist Matching"
          status={panelStatus}
          summary={panelSummary(drive)}
        />
      </div>

      {drive.status === 'REJECTED_BACKGROUND' && bgFlags.length > 0 && (
        <div className="detail-card rejection">
          <h3>Rejection Flags</h3>
          <ul>
            {bgFlags.map((f, i) => (
              <li key={i}>
                <strong>[{f.severity.toUpperCase()}]</strong> {f.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {drive.status === 'REJECTED_FIT' && drive.jd_match && (
        <div className="detail-card rejection">
          <h3>Fit Report — Not Proceeding</h3>
          <p>Score: <strong>{drive.jd_match.score}</strong></p>
          {drive.jd_match.missing?.length > 0 && (
            <p>Missing skills: {drive.jd_match.missing.join(', ')}</p>
          )}
        </div>
      )}

      {drive.status === 'HOLD_FIT' && drive.jd_match && (
        <div className="detail-card hold">
          <h3>Hold — Human Decision Required</h3>
          <p>Score: <strong>{drive.jd_match.score}</strong></p>
          {drive.jd_match.missing?.length > 0 && (
            <p>Gaps: {drive.jd_match.missing.join(', ')}</p>
          )}
          <p className="muted">Cancel and resubmit with an updated JD or candidate profile to proceed.</p>
        </div>
      )}

      {isFailed && drive.error && (
        <div className="detail-card rejection">
          <h3>Drive Failed</h3>
          <p>{drive.error}</p>
        </div>
      )}

      <div className="drive-actions">
        {isCompleted && (
          <button className="btn-primary" onClick={() => onViewPack(driveId)}>
            View Interview Readiness Pack →
          </button>
        )}
        <button className="btn-secondary" onClick={onNewDrive}>
          Start New Drive
        </button>
      </div>
    </div>
  );
}
