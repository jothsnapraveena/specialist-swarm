const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res;
}

export async function createCandidate(resumeText) {
  const res = await request('/candidates', {
    method: 'POST',
    body: JSON.stringify({ resume_text: resumeText }),
  });
  return res.json();
}

export async function createJob(jdText) {
  const res = await request('/jobs', {
    method: 'POST',
    body: JSON.stringify({ jd_text: jdText }),
  });
  return res.json();
}

export async function getPanelists() {
  const res = await request('/panelists');
  return res.json();
}

export async function updatePanelists(pool) {
  const res = await request('/panelists', {
    method: 'PUT',
    body: JSON.stringify(pool),
  });
  return res.json();
}

export async function createDrive(candidateId, jobId) {
  const res = await request('/drives', {
    method: 'POST',
    body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
  });
  return res.json();
}

export async function getDrive(driveId) {
  const res = await request(`/drives/${driveId}`);
  return res.json();
}

export async function getDriveReport(driveId, format = 'json') {
  const res = await request(`/drives/${driveId}/report?format=${format}`, {
    headers: {},
  });
  return format === 'json' ? res.json() : res.blob();
}

export function openDriveReportDownload(driveId) {
  window.open(`${BASE_URL}/drives/${driveId}/report?format=docx`, '_blank');
}
