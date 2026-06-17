import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function NewDrive({ onDriveStarted }) {
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [loadingSample, setLoadingSample] = useState(false);
  const [candidateText, setCandidateText] = useState("");
  const [jobText, setJobText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listSamples().then(setRoles).catch((err) => setError(err.message));
  }, []);

  async function loadRole(role) {
    setError(null);
    setLoadingSample(true);
    try {
      const sample = await api.getSample(role);
      setCandidateText(sample.candidate_text);
      setJobText(sample.jd_text);
      setSelectedRole(role);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSample(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { candidate_id } = await api.createCandidate(candidateText);
      const { job_id } = await api.createJob(jobText);
      const drive = await api.createDrive(candidate_id, job_id);
      onDriveStarted(drive.drive_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <span className="eyebrow">● Stage 1 of 3</span>
      <h1>Start a Recruitment Drive</h1>
      <p className="subtitle">
        Pick a role to auto-fill a candidate + job description from the
        sample pool, or paste your own below. The swarm runs a sequential,
        gated pipeline — background check, then JD match, then panel match —
        and stops early the moment a gate fails.
      </p>
      {error && <div className="error-banner">⚠ {error}</div>}

      {roles.length > 0 && (
        <div className="card">
          <div className="card-header-row">
            <h2>📁 Sample data pool</h2>
            {loadingSample && <span className="loading-line" style={{ padding: 0 }}><span className="spinner" />loading…</span>}
          </div>
          <div className="toolbar" style={{ marginTop: 0, flexWrap: "wrap" }}>
            {roles.map((r) => (
              <button
                key={r.role}
                type="button"
                className={selectedRole === r.role ? "primary" : "secondary"}
                onClick={() => loadRole(r.role)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="card">
          <div className="field-row">
            <div>
              <div className="field-label-row">
                <label htmlFor="candidate">Candidate resume / profile</label>
              </div>
              <textarea
                id="candidate"
                value={candidateText}
                onChange={(e) => { setCandidateText(e.target.value); setSelectedRole(null); }}
                placeholder="Paste resume text, or pick a role above…"
                required
              />
            </div>
            <div>
              <div className="field-label-row">
                <label htmlFor="jd">Job description</label>
              </div>
              <textarea
                id="jd"
                value={jobText}
                onChange={(e) => { setJobText(e.target.value); setSelectedRole(null); }}
                placeholder="Paste job description text, or pick a role above…"
                required
              />
            </div>
          </div>
          <button className="primary" type="submit" disabled={submitting}>
            {submitting ? "Starting drive…" : "Start Drive →"}
          </button>
        </div>
      </form>
    </div>
  );
}
