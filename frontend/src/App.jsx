import { useState } from 'react';
import NewDrive from './components/NewDrive';
import DriveStatus from './components/DriveStatus';
import ReadinessPack from './components/ReadinessPack';
import PanelistPool from './components/PanelistPool';
import './App.css';

export default function App() {
  const [screen, setScreen] = useState('new-drive');
  const [driveId, setDriveId] = useState(null);

  function handleDriveCreated(id) {
    setDriveId(id);
    setScreen('drive-status');
  }

  function handleViewPack(id) {
    setDriveId(id);
    setScreen('readiness-pack');
  }

  function handleNewDrive() {
    setDriveId(null);
    setScreen('new-drive');
  }

  return (
    <div className="app">
      <nav className="top-nav">
        <div className="nav-brand">Recruitment Drive Console</div>
        <div className="nav-links">
          <button
            className={`nav-link ${screen === 'new-drive' ? 'active' : ''}`}
            onClick={handleNewDrive}
          >
            New Drive
          </button>
          {driveId && (
            <button
              className={`nav-link ${screen === 'drive-status' ? 'active' : ''}`}
              onClick={() => setScreen('drive-status')}
            >
              Drive Status
            </button>
          )}
          {driveId && screen === 'readiness-pack' && (
            <button className="nav-link active">Readiness Pack</button>
          )}
          <button
            className={`nav-link ${screen === 'panelist-pool' ? 'active' : ''}`}
            onClick={() => setScreen('panelist-pool')}
          >
            Panelist Pool
          </button>
        </div>
      </nav>

      <main className="main-content">
        {screen === 'new-drive' && (
          <NewDrive
            onDriveCreated={handleDriveCreated}
            onEditPool={() => setScreen('panelist-pool')}
          />
        )}
        {screen === 'drive-status' && driveId && (
          <DriveStatus
            driveId={driveId}
            onViewPack={handleViewPack}
            onNewDrive={handleNewDrive}
          />
        )}
        {screen === 'readiness-pack' && driveId && (
          <ReadinessPack
            driveId={driveId}
            onBack={() => setScreen('drive-status')}
            onNewDrive={handleNewDrive}
          />
        )}
        {screen === 'panelist-pool' && (
          <PanelistPool onBack={() => setScreen(driveId ? 'drive-status' : 'new-drive')} />
        )}
      </main>
    </div>
  );
}
