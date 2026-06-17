import { useEffect, useState } from "react";
import { api } from "../api.js";

function emptyPanelist() {
  return {
    id: `p_${Math.random().toString(36).slice(2, 8)}`,
    name: "",
    skills: [],
    location: "",
    availability: [{ date: "", slots: 1 }],
  };
}

export default function PanelistPool() {
  const [pool, setPool] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getPanelists().then(setPool).catch((err) => setError(err.message));
  }, []);

  function updatePanelist(index, field, value) {
    const next = { ...pool, panelist_pool: [...pool.panelist_pool] };
    next.panelist_pool[index] = { ...next.panelist_pool[index], [field]: value };
    setPool(next);
    setSaved(false);
  }

  function updateAvailability(index, field, value) {
    const next = { ...pool, panelist_pool: [...pool.panelist_pool] };
    const avail = [...(next.panelist_pool[index].availability || [{ date: "", slots: 1 }])];
    avail[0] = { ...avail[0], [field]: field === "slots" ? Number(value) : value };
    next.panelist_pool[index] = { ...next.panelist_pool[index], availability: avail };
    setPool(next);
    setSaved(false);
  }

  function removePanelist(index) {
    const next = { ...pool, panelist_pool: pool.panelist_pool.filter((_, i) => i !== index) };
    setPool(next);
    setSaved(false);
  }

  function addPanelist() {
    setPool({ ...pool, panelist_pool: [...pool.panelist_pool, emptyPanelist()] });
    setSaved(false);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const result = await api.putPanelists(pool);
      setPool(result);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (error && !pool) return <div className="error-banner">⚠ {error}</div>;
  if (!pool) {
    return (
      <div className="loading-line">
        <span className="spinner" /> Loading panelist pool…
      </div>
    );
  }

  return (
    <div>
      <span className="eyebrow">⚙ Configuration</span>
      <h1>Panelist Pool</h1>
      <p className="subtitle">
        Skill overlap is computed first, availability second, then mode
        (In-Person / Online) by comparing the candidate's and panelist's
        location — see <code>panelist-matching-policy</code>.
      </p>
      {error && <div className="error-banner">⚠ {error}</div>}

      <div className="card">
        <div className="card-header-row">
          <h2>📅 Interview window</h2>
        </div>
        <input
          id="interview_date"
          value={pool.interview_date || ""}
          onChange={(e) => { setPool({ ...pool, interview_date: e.target.value }); setSaved(false); }}
          placeholder="YYYY-MM-DD"
          style={{ maxWidth: 220 }}
        />
      </div>

      <div className="card">
        <h2>👥 Panelists</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Skills</th>
              <th>Location</th>
              <th>Available</th>
              <th>Slots</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pool.panelist_pool.map((p, i) => (
              <tr key={p.id}>
                <td>
                  <input value={p.name} onChange={(e) => updatePanelist(i, "name", e.target.value)} />
                </td>
                <td>
                  <input
                    value={(p.skills || []).join(", ")}
                    onChange={(e) =>
                      updatePanelist(i, "skills", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
                    }
                  />
                </td>
                <td>
                  <input value={p.location} onChange={(e) => updatePanelist(i, "location", e.target.value)} />
                </td>
                <td>
                  <input
                    value={p.availability?.[0]?.date || ""}
                    onChange={(e) => updateAvailability(i, "date", e.target.value)}
                    placeholder="YYYY-MM-DD"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    value={p.availability?.[0]?.slots ?? 1}
                    onChange={(e) => updateAvailability(i, "slots", e.target.value)}
                  />
                </td>
                <td>
                  <button className="secondary" onClick={() => removePanelist(i)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="toolbar">
          <button className="secondary" onClick={addPanelist}>+ Add panelist</button>
          <button className="primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save Pool"}
          </button>
          {saved && <span className="badge badge-green">Saved ✓</span>}
        </div>
      </div>
    </div>
  );
}
