import { useState } from "react";
import NewDrive from "./screens/NewDrive.jsx";
import DriveStatus from "./screens/DriveStatus.jsx";
import Results from "./screens/Results.jsx";
import PanelistPool from "./screens/PanelistPool.jsx";

const TABS = [
  { key: "new", label: "New Drive" },
  { key: "status", label: "Drive Status" },
  { key: "results", label: "Results" },
  { key: "panelists", label: "Panelist Pool" },
];

export default function App() {
  const [view, setView] = useState("new");
  const [driveId, setDriveId] = useState(null);

  function handleDriveStarted(id) {
    setDriveId(id);
    setView("status");
  }

  function handleViewResults(id) {
    setDriveId(id);
    setView("results");
  }

  return (
    <div className="app">
      <nav className="nav">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={view === tab.key ? "active" : ""}
            onClick={() => setView(tab.key)}
            disabled={(tab.key === "status" || tab.key === "results") && !driveId}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {view === "new" && <NewDrive onDriveStarted={handleDriveStarted} />}
      {view === "status" && driveId && (
        <DriveStatus driveId={driveId} onViewResults={handleViewResults} />
      )}
      {view === "results" && driveId && <Results driveId={driveId} />}
      {view === "panelists" && <PanelistPool />}
    </div>
  );
}
