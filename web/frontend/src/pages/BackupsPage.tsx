import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  Archive,
  Plus,
  RefreshCw,
  Download,
  Trash2,
  AlertCircle,
  Clock,
  HardDrive,
  Loader2,
} from 'lucide-react';
import { Backup, Server } from '../types';

interface BackupsPageProps {
  server: Server | null;
}

export function BackupsPage({ server }: BackupsPageProps) {
  const { id } = useParams<{ id: string }>();
  const serverId = id ? parseInt(id) : null;

  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchBackups = useCallback(async () => {
    if (!serverId) return;

    try {
      setLoading(true);
      const res = await fetch(`/api/v1/servers/${serverId}/backups`);
      if (res.ok) {
        const data = await res.json();
        setBackups(Array.isArray(data) ? data : []);
        setError(null);
      } else {
        setError('Failed to fetch backups');
      }
    } catch (e) {
      setError('Failed to fetch backups');
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    fetchBackups();
  }, [fetchBackups]);

  const handleCreateBackup = async (stopFirst: boolean) => {
    if (!serverId) return;

    setCreating(true);
    try {
      const res = await fetch(`/api/v1/servers/${serverId}/backups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stop_first: stopFirst, backup_type: 'manual' }),
      });

      if (res.ok) {
        setShowCreateModal(false);
        fetchBackups();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create backup');
      }
    } catch (e) {
      setError('Failed to create backup');
    } finally {
      setCreating(false);
    }
  };

  const handleRestore = async (backupId: number) => {
    if (!confirm('Are you sure you want to restore this backup? This will overwrite current server files.')) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/backups/${backupId}/restore`, {
        method: 'POST',
      });

      if (res.ok) {
        alert('Backup restored successfully');
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to restore backup');
      }
    } catch (e) {
      setError('Failed to restore backup');
    }
  };

  const handleDelete = async (backupId: number) => {
    if (!confirm('Are you sure you want to delete this backup?')) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/backups/${backupId}?delete_file=true`, {
        method: 'DELETE',
      });

      if (res.ok) {
        fetchBackups();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to delete backup');
      }
    } catch (e) {
      setError('Failed to delete backup');
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  if (!serverId) {
    return (
      <div className="p-6">
        <div className="card text-center py-12">
          <AlertCircle className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Server Selected</h3>
          <p className="text-foreground-muted">Select a server from the dashboard to manage backups.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Backups</h1>
          <p className="text-foreground-muted mt-1">
            {server?.name || `Server ${serverId}`} - {backups.length} backup{backups.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={fetchBackups} className="btn btn-ghost">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Create Backup
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-destructive/20 border border-destructive rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <span className="text-destructive">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-destructive hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-foreground-muted">Loading backups...</p>
          </div>
        </div>
      ) : backups.length === 0 ? (
        <div className="card text-center py-16">
          <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
            <Archive className="w-8 h-8 text-foreground-muted" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No Backups Yet</h3>
          <p className="text-foreground-muted mb-6">
            Create your first backup to protect your server data
          </p>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Create Backup
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {backups.map((backup) => (
            <div key={backup.id} className="card card-hover">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-secondary rounded-lg flex items-center justify-center">
                    <Archive className="w-5 h-5 text-primary" />
                  </div>

                  <div>
                    <h3 className="font-medium">{backup.filename}</h3>
                    <div className="flex items-center gap-4 text-sm text-foreground-muted mt-1">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDate(backup.created_at)}
                      </span>
                      <span className="flex items-center gap-1">
                        <HardDrive className="w-3.5 h-3.5" />
                        {formatSize(backup.size_bytes)}
                      </span>
                      <span className="px-2 py-0.5 bg-secondary rounded text-xs uppercase">
                        {backup.backup_type}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRestore(backup.id)}
                    className="btn btn-secondary btn-sm"
                  >
                    <Download className="w-4 h-4" />
                    Restore
                  </button>
                  <button
                    onClick={() => handleDelete(backup.id)}
                    className="btn btn-ghost btn-sm text-destructive"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Backup Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card w-full max-w-md mx-4">
            <h2 className="text-xl font-semibold mb-4">Create Backup</h2>

            <p className="text-foreground-muted mb-6">
              Create a backup of your server files. This may take a few minutes depending on server size.
            </p>

            <div className="space-y-4 mb-6">
              <button
                onClick={() => handleCreateBackup(false)}
                disabled={creating}
                className="w-full card card-hover text-left"
              >
                <h3 className="font-medium">Quick Backup</h3>
                <p className="text-sm text-foreground-muted">
                  Backup while server is running. Fast but may miss recent changes.
                </p>
              </button>

              <button
                onClick={() => handleCreateBackup(true)}
                disabled={creating}
                className="w-full card card-hover text-left"
              >
                <h3 className="font-medium">Safe Backup</h3>
                <p className="text-sm text-foreground-muted">
                  Stop server first for a complete backup. Server will restart after.
                </p>
              </button>
            </div>

            {creating && (
              <div className="flex items-center gap-3 mb-4 p-3 bg-secondary rounded-lg">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span>Creating backup...</span>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={creating}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
