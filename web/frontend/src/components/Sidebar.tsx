import { Link, useLocation } from 'react-router-dom';
import {
  Server,
  LayoutDashboard,
  Terminal,
  FolderArchive,
  Puzzle,
  Clock,
  Settings,
  Coffee,
  ChevronRight
} from 'lucide-react';

interface SidebarProps {
  currentServer: { id: number; name: string; is_running?: boolean } | null;
}

export function Sidebar({ currentServer }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;
  const isPathActive = (pattern: string) => location.pathname.includes(pattern);

  return (
    <aside className="w-60 sidebar h-screen flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-card-border">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 bg-primary rounded-lg flex items-center justify-center group-hover:glow-primary-sm transition-shadow">
            <Server className="w-5 h-5 text-black" />
          </div>
          <div>
            <h1 className="font-semibold text-foreground tracking-tight">MSM</h1>
            <p className="text-[10px] text-foreground-muted uppercase tracking-widest">Server Manager</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <Link
          to="/"
          className={`sidebar-item ${isActive('/') ? 'sidebar-item-active' : ''}`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span className="text-sm">Dashboard</span>
        </Link>

        {currentServer && (
          <>
            <div className="pt-5 pb-2">
              <div className="px-3 flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${currentServer.is_running ? 'bg-online pulse-dot' : 'bg-offline'}`} />
                <p className="text-xs font-medium text-foreground-muted truncate flex-1">
                  {currentServer.name}
                </p>
                <ChevronRight className="w-3 h-3 text-foreground-muted" />
              </div>
            </div>

            <Link
              to={`/server/${currentServer.id}/console`}
              className={`sidebar-item ${isPathActive('/console') ? 'sidebar-item-active' : ''}`}
            >
              <Terminal className="w-4 h-4" />
              <span className="text-sm">Console</span>
            </Link>

            <Link
              to={`/server/${currentServer.id}/backups`}
              className={`sidebar-item ${isPathActive('/backups') ? 'sidebar-item-active' : ''}`}
            >
              <FolderArchive className="w-4 h-4" />
              <span className="text-sm">Backups</span>
            </Link>

            <Link
              to={`/server/${currentServer.id}/plugins`}
              className={`sidebar-item ${isPathActive('/plugins') ? 'sidebar-item-active' : ''}`}
            >
              <Puzzle className="w-4 h-4" />
              <span className="text-sm">Plugins</span>
            </Link>

            <Link
              to={`/server/${currentServer.id}/schedules`}
              className={`sidebar-item ${isPathActive('/schedules') ? 'sidebar-item-active' : ''}`}
            >
              <Clock className="w-4 h-4" />
              <span className="text-sm">Schedules</span>
            </Link>

            <Link
              to={`/server/${currentServer.id}/settings`}
              className={`sidebar-item ${isPathActive('/settings') ? 'sidebar-item-active' : ''}`}
            >
              <Settings className="w-4 h-4" />
              <span className="text-sm">Settings</span>
            </Link>
          </>
        )}

        <div className="pt-5 pb-2">
          <p className="px-3 text-[10px] font-semibold text-foreground-muted uppercase tracking-widest">
            System
          </p>
        </div>

        <Link
          to="/java"
          className={`sidebar-item ${isActive('/java') ? 'sidebar-item-active' : ''}`}
        >
          <Coffee className="w-4 h-4" />
          <span className="text-sm">Java Runtimes</span>
        </Link>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-card-border">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-foreground-muted uppercase tracking-wider">v0.2.0</span>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-online" />
            <span className="text-[10px] text-foreground-muted">API Connected</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
