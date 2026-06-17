import { useState, useEffect } from 'react';
import { createCandidate, createJob, createDrive, getPanelists } from '../api';

export default function NewDrive({ onDriveCreated, onEditPool }) {
  const [resumeText, setResumeText] = useState('');
  const [jdText, setJdText] = useState('');
  const [panelistCount, setPanelistCount] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getPanelists()
      .then((pool) => setPanelistCount(Array.isArray(pool) ? pool.length : 0))
      .catch(() => setPanelistCount(0));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!resumeText.trim()) return setError('Resume text is required.');
    if (!jdText.trim()) return setError('Job description is required.');

    setError('');
    setLoading(true);
    try {
      const [{ candidate_id }, { job_id }] = await Promise.all([
        createCandidate(resumeText.trim()),
        createJob(jdText.trim()),
      ]);
      const { drive_id } = await createDrive(candidate_id, job_id);
      onDriveCreated(drive_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="screen">
      <h2>New Recruitment Drive</h2>

      <div className="panelist-notice">
        {panelistCount === null ? (
          'Loading panelist pool…'
        ) : (
          <>
            Panelist pool: <strong>{panelistCount} panelist{panelistCount !== 1 ? 's' : ''}</strong>{' '}
            <button className="link-btn" onClick={onEditPool}>
              Edit pool
            </button>
          </>
        )}
      </div>

      <form onSubmit={handleSubmit} className="drive-form">
        <div className="form-group">
          <label htmlFor="resume">Candidate Resume / Profile</label>
          <textarea
            id="resume"
            rows={12}
            placeholder="Paste resume or candidate profile text here…"
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="jd">Job Description</label>
          <textarea
            id="jd"
            rows={12}
            placeholder="Paste job description here…"
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            disabled={loading}
          />
        </div>

        {error && <div className="error-banner">{error}</div>}

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Starting drive…' : 'Start Recruitment Drive →'}
        </button>
      </form>
    </div>
  );
}
