import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar, StatsBar } from './components';
import {
  Dashboard,
  ConsolePage,
  SettingsPage,
  BackupsPage,
  PluginsPage,
  SchedulesPage,
  JavaPage,
} from './pages';
import { useSystemStats } from './hooks';
import { Server } from './types';

function App() {
  const [currentServer, setCurrentServer] = useState<Server | null>(null);
  const { stats } = useSystemStats();

  // Load last selected server from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('currentServer');
    if (saved) {
      try {
        setCurrentServer(JSON.parse(saved));
      } catch (e) {
        // Ignore
      }
    }
  }, []);

  const handleSelectServer = (server: Server) => {
    setCurrentServer(server);
    localStorage.setItem('currentServer', JSON.stringify(server));
  };

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-background">
        {/* Sidebar */}
        <Sidebar currentServer={currentServer} />

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Stats Bar */}
          <StatsBar stats={stats} />

          {/* Page Content */}
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route
                path="/"
                element={<Dashboard onSelectServer={handleSelectServer} />}
              />
              <Route
                path="/server/:id/console"
                element={<ConsolePage server={currentServer} />}
              />
              <Route
                path="/server/:id/settings"
                element={<SettingsPage server={currentServer} />}
              />
              <Route
                path="/server/:id/backups"
                element={<BackupsPage server={currentServer} />}
              />
              <Route
                path="/server/:id/plugins"
                element={<PluginsPage server={currentServer} />}
              />
              <Route
                path="/server/:id/schedules"
                element={<SchedulesPage server={currentServer} />}
              />
              <Route
                path="/java"
                element={<JavaPage />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
