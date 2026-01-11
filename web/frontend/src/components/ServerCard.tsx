import { Play, Square, RotateCw, Terminal, Settings, Cpu, HardDrive } from 'lucide-react';
import { Server } from '../types';
import { useState } from 'react';
import { Link } from 'react-router-dom';

interface ServerCardProps {
  server: Server;
  onStart: (id: number) => Promise<void>;
  onStop: (id: number) => Promise<void>;
  onRestart: (id: number) => Promise<void>;
  onSelect: (server: Server) => void;
}

export function ServerCard({ server, onStart, onStop, onRestart, onSelect }: ServerCardProps) {
  const [loading, setLoading] = useState(false);

  const handleAction = async (action: () => Promise<void>) => {
    setLoading(true);
    try {
      await action();
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = () => {
    if (loading) return 'status-starting';
    return server.is_running ? 'status-online' : 'status-offline';
  };

  const getStatusText = () => {
    if (loading) return 'Processing...';
    return server.is_running ? 'Online' : 'Offline';
  };

  return (
    <div className={`card card-hover server-card group ${server.is_running ? 'server-card-running' : ''}`}>
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-3">
          {/* Server Icon */}
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 ${
            server.is_running
              ? 'bg-primary/15 group-hover:bg-primary/25'
              : 'bg-secondary group-hover:bg-secondary-hover'
          }`}>
            <div className={`w-2.5 h-2.5 rounded-full transition-colors ${
              loading
                ? 'bg-starting animate-pulse'
                : server.is_running
                  ? 'bg-online pulse-dot'
                  : 'bg-offline'
            }`} />
          </div>

          <div>
            <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
              {server.name}
            </h3>
            <p className="text-xs text-foreground-muted mt-0.5 uppercase tracking-wide">
              {server.type} {server.version}
            </p>
          </div>
        </div>

        <span className={`status-badge ${getStatusClass()}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            loading ? 'bg-starting animate-pulse' : server.is_running ? 'bg-online' : 'bg-offline'
          }`} />
          {getStatusText()}
        </span>
      </div>

      {/* Server Info */}
      <div className="flex items-center gap-6 mb-5 text-sm">
        <div className="flex items-center gap-2">
          <HardDrive className="w-3.5 h-3.5 text-foreground-muted" />
          <span className="text-foreground-muted">Port</span>
          <span className="font-medium text-foreground">{server.port}</span>
        </div>
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-foreground-muted" />
          <span className="text-foreground-muted">RAM</span>
          <span className="font-medium text-foreground">{server.memory}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-4 border-t border-card-border">
        {server.is_running ? (
          <>
            <button
              onClick={() => handleAction(() => onStop(server.id))}
              disabled={loading}
              className="btn btn-destructive btn-sm flex-1"
            >
              <Square className="w-3.5 h-3.5" />
              Stop
            </button>
            <button
              onClick={() => handleAction(() => onRestart(server.id))}
              disabled={loading}
              className="btn btn-secondary btn-sm flex-1"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Restart
            </button>
          </>
        ) : (
          <button
            onClick={() => handleAction(() => onStart(server.id))}
            disabled={loading}
            className="btn btn-primary btn-sm flex-1"
          >
            <Play className="w-3.5 h-3.5" />
            Start Server
          </button>
        )}

        <Link
          to={`/server/${server.id}/console`}
          onClick={() => onSelect(server)}
          className="btn btn-ghost btn-sm btn-icon"
          title="Console"
        >
          <Terminal className="w-4 h-4" />
        </Link>

        <Link
          to={`/server/${server.id}/settings`}
          onClick={() => onSelect(server)}
          className="btn btn-ghost btn-sm btn-icon"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
