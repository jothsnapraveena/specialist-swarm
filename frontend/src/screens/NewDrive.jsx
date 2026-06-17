import { useState } from "react";
import { api } from "../api.js";

const SAMPLE_CANDIDATE = `# Candidate Profile — Priya Nair

Location: Bengaluru, India
...paste a resume, or use the synthetic-data/candidate-profile.md sample.`;

const SAMPLE_JD = `# Job Description — Senior Backend Engineer

Must-have skills: Python, Kubernetes, System Design, SQL
...paste a JD, or use the synthetic-data/sample_jd.md sample.`;

export default function NewDrive({ onDriveStarted }) {
  const [candidateText, setCandidateText] = useState("");
  const [jobText, setJobText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

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
      <h1>New Drive</h1>
      <p className="subtitle">
        Paste a candidate resume and a job description. The drive runs the
        gated pipeline: background check, then JD match, then panel match —
        stopping early on a rejection.
      </p>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="card">
          <label htmlFor="candidate">Candidate resume / profile</label>
          <textarea
            id="candidate"
            value={candidateText}
            onChange={(e) => setCandidateText(e.target.value)}
            placeholder={SAMPLE_CANDIDATE}
            required
          />
          <label htmlFor="jd">Job description</label>
          <textarea
            id="jd"
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
            placeholder={SAMPLE_JD}
            required
          />
          <button className="primary" type="submit" disabled={submitting}>
            {submitting ? "Starting drive…" : "Start Drive"}
          </button>
        </div>
      </form>
    </div>
  );
}
