import { useState } from 'react';
import { Plus, RefreshCw, Server, Zap } from 'lucide-react';
import { ServerCard, CreateServerModal } from '../components';
import { useServers } from '../hooks';
import { Server as ServerType } from '../types';

interface DashboardProps {
  onSelectServer: (server: ServerType) => void;
}

export function Dashboard({ onSelectServer }: DashboardProps) {
  const { servers, loading, error, refetch } = useServers();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const handleStart = async (id: number) => {
    await fetch(`/api/v1/servers/${id}/start`, { method: 'POST' });
    refetch();
  };

  const handleStop = async (id: number) => {
    await fetch(`/api/v1/servers/${id}/stop`, { method: 'POST' });
    refetch();
  };

  const handleRestart = async (id: number) => {
    await fetch(`/api/v1/servers/${id}/restart`, { method: 'POST' });
    refetch();
  };

  const runningCount = servers.filter(s => s.is_running).length;
  const totalCount = servers.length;

  return (
    <div className="p-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Dashboard</h1>
          <p className="text-foreground-muted mt-1 text-sm">
            <span className={runningCount > 0 ? 'text-primary font-medium' : ''}>
              {runningCount}
            </span>
            {' '}of {totalCount} servers running
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="btn btn-ghost"
            disabled={isRefreshing}
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            New Server
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-12 h-12 border-3 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-foreground-muted text-sm">Loading servers...</p>
          </div>
        </div>
      ) : error ? (
        <div className="card bg-destructive/10 border-destructive text-center py-12 animate-slideUp">
          <p className="text-destructive font-medium">{error}</p>
          <button onClick={handleRefresh} className="btn btn-secondary mt-4">
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      ) : servers.length === 0 ? (
        <div className="card text-center py-16 animate-slideUp">
          <div className="w-20 h-20 bg-secondary rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Server className="w-10 h-10 text-foreground-muted" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No Servers Yet</h3>
          <p className="text-foreground-muted mb-8 max-w-sm mx-auto">
            Create your first Minecraft server to get started
          </p>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary btn-lg">
            <Zap className="w-5 h-5" />
            Create Your First Server
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {servers.map((server, index) => (
            <div
              key={server.id}
              className="animate-slideUp"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <ServerCard
                server={server}
                onStart={handleStart}
                onStop={handleStop}
                onRestart={handleRestart}
                onSelect={onSelectServer}
              />
            </div>
          ))}
        </div>
      )}

      {/* Create Server Modal */}
      <CreateServerModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={refetch}
      />
    </div>
  );
}
