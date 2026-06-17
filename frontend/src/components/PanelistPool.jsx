import { useState, useEffect } from 'react';
import { getPanelists, updatePanelists } from '../api';

export default function PanelistPool({ onBack }) {
  const [pool, setPool] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [parseError, setParseError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getPanelists()
      .then((data) => setPool(data))
      .catch((err) => setError(err.message));
  }, []);

  function openEditor() {
    setDraft(JSON.stringify(pool, null, 2));
    setParseError('');
    setEditing(true);
    setSaved(false);
  }

  async function handleSave() {
    let parsed;
    try {
      parsed = JSON.parse(draft);
    } catch {
      setParseError('Invalid JSON — fix the syntax and try again.');
      return;
    }
    if (!Array.isArray(parsed)) {
      setParseError('Pool must be a JSON array.');
      return;
    }
    setParseError('');
    setSaving(true);
    try {
      const updated = await updatePanelists(parsed);
      setPool(updated);
      setEditing(false);
      setSaved(true);
    } catch (err) {
      setParseError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return (
      <div className="screen">
        <div className="error-banner">{error}</div>
        <button className="btn-secondary" onClick={onBack}>Back</button>
      </div>
    );
  }

  if (!pool) {
    return <div className="screen"><div className="loading">Loading panelist pool…</div></div>;
  }

  return (
    <div className="screen">
      <div className="drive-header">
        <div>
          <h2>Panelist Pool</h2>
          <span className="drive-id">{pool.length} panelist{pool.length !== 1 ? 's' : ''}</span>
        </div>
        {!editing && (
          <button className="btn-primary" onClick={openEditor}>Edit Pool (JSON)</button>
        )}
      </div>

      {saved && <div className="success-banner">Pool saved successfully.</div>}

      {!editing ? (
        <div className="report-card">
          <table className="report-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Location</th>
                <th>Skills</th>
                <th>Availability</th>
              </tr>
            </thead>
            <tbody>
              {pool.map((p, i) => (
                <tr key={p.id ?? i}>
                  <td><strong>{p.name}</strong></td>
                  <td>{p.location}</td>
                  <td>
                    <div className="tag-list">
                      {(p.skills || []).map((s) => (
                        <span key={s} className="tag tag-skill">{s}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    {(p.availability || []).map((a, j) => (
                      <div key={j}>{a.date}: {(a.slots || []).join(', ')}</div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="report-card">
          <p className="muted">
            Edit the JSON array below. Each panelist must have: <code>id</code>, <code>name</code>,{' '}
            <code>skills</code>, <code>location</code>, <code>availability</code>.
          </p>
          <textarea
            className="json-editor"
            rows={Math.max(20, pool.length * 10)}
            value={draft}
            onChange={(e) => { setDraft(e.target.value); setParseError(''); }}
            spellCheck={false}
          />
          {parseError && <div className="error-banner">{parseError}</div>}
          <div className="editor-actions">
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save Pool'}
            </button>
            <button className="btn-secondary" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="drive-actions">
        <button className="btn-secondary" onClick={onBack}>← Back</button>
      </div>
    </div>
  );
}
