const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  createCandidate: (text) =>
    request("/candidates", { method: "POST", body: JSON.stringify({ text }) }),
  createJob: (text) =>
    request("/jobs", { method: "POST", body: JSON.stringify({ text }) }),
  listSamples: () => request("/samples"),
  getSample: (role) => request(`/samples/${role}`),
  getPanelists: () => request("/panelists"),
  putPanelists: (data) =>
    request("/panelists", { method: "PUT", body: JSON.stringify(data) }),
  createDrive: (candidate_id, job_id) =>
    request("/drives", { method: "POST", body: JSON.stringify({ candidate_id, job_id }) }),
  getDrive: (driveId) => request(`/drives/${driveId}`),
  getReport: (driveId) => request(`/drives/${driveId}/report`),
  baseUrl: BASE_URL,
};
