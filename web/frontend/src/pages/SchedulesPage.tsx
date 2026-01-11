import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  Calendar,
  Plus,
  Trash2,
  AlertCircle,
  Clock,
  Play,
  Square,
  RefreshCw,
  Archive,
  Terminal,
  ToggleLeft,
  ToggleRight,
  Loader2,
  X,
} from 'lucide-react';
import { Server } from '../types';

interface Schedule {
  id: number;
  server_id: number;
  action: string;
  cron: string;
  payload: string | null;
  enabled: boolean;
  next_run: string | null;
  last_run: string | null;
  created_at: string;
}

interface SchedulesPageProps {
  server: Server | null;
}

const ACTION_TYPES = [
  { id: 'start', name: 'Start Server', icon: Play, description: 'Start the server' },
  { id: 'stop', name: 'Stop Server', icon: Square, description: 'Stop the server gracefully' },
  { id: 'restart', name: 'Restart Server', icon: RefreshCw, description: 'Restart the server' },
  { id: 'backup', name: 'Create Backup', icon: Archive, description: 'Create a server backup' },
  { id: 'command', name: 'Run Command', icon: Terminal, description: 'Execute a console command' },
];

const CRON_PRESETS = [
  { label: 'Every hour', cron: '0 * * * *' },
  { label: 'Every 6 hours', cron: '0 */6 * * *' },
  { label: 'Daily at midnight', cron: '0 0 * * *' },
  { label: 'Daily at 6 AM', cron: '0 6 * * *' },
  { label: 'Weekly on Sunday', cron: '0 0 * * 0' },
  { label: 'Monthly', cron: '0 0 1 * *' },
];

export function SchedulesPage({ server }: SchedulesPageProps) {
  const { id } = useParams<{ id: string }>();
  const serverId = id ? parseInt(id) : null;

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // Create form state
  const [formAction, setFormAction] = useState('backup');
  const [formCron, setFormCron] = useState('0 0 * * *');
  const [formPayload, setFormPayload] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);

  const fetchSchedules = useCallback(async () => {
    if (!serverId) return;

    try {
      setLoading(true);
      const res = await fetch(`/api/v1/servers/${serverId}/schedules`);
      if (res.ok) {
        const data = await res.json();
        setSchedules(Array.isArray(data) ? data : []);
        setError(null);
      } else {
        setError('Failed to fetch schedules');
      }
    } catch (e) {
      setError('Failed to fetch schedules');
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!serverId) return;

    setCreating(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/servers/${serverId}/schedules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: formAction,
          cron: formCron,
          payload: formAction === 'command' ? formPayload : null,
          enabled: formEnabled,
        }),
      });

      if (res.ok) {
        setShowCreateModal(false);
        resetForm();
        fetchSchedules();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create schedule');
      }
    } catch (e) {
      setError('Failed to create schedule');
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (schedule: Schedule) => {
    try {
      const res = await fetch(`/api/v1/schedules/${schedule.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !schedule.enabled }),
      });

      if (res.ok) {
        fetchSchedules();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to toggle schedule');
      }
    } catch (e) {
      setError('Failed to toggle schedule');
    }
  };

  const handleDelete = async (scheduleId: number) => {
    if (!confirm('Are you sure you want to delete this schedule?')) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/schedules/${scheduleId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        fetchSchedules();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to delete schedule');
      }
    } catch (e) {
      setError('Failed to delete schedule');
    }
  };

  const resetForm = () => {
    setFormAction('backup');
    setFormCron('0 0 * * *');
    setFormPayload('');
    setFormEnabled(true);
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getActionInfo = (actionId: string) => {
    return ACTION_TYPES.find((a) => a.id === actionId) || ACTION_TYPES[0];
  };

  const describeCron = (cron: string): string => {
    const preset = CRON_PRESETS.find((p) => p.cron === cron);
    if (preset) return preset.label;
    return cron;
  };

  if (!serverId) {
    return (
      <div className="p-6">
        <div className="card text-center py-12">
          <AlertCircle className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Server Selected</h3>
          <p className="text-foreground-muted">Select a server from the dashboard to manage schedules.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Schedules</h1>
          <p className="text-foreground-muted mt-1">
            {server?.name || `Server ${serverId}`} - {schedules.length} schedule{schedules.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={fetchSchedules} className="btn btn-ghost">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Create Schedule
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
            <p className="text-foreground-muted">Loading schedules...</p>
          </div>
        </div>
      ) : schedules.length === 0 ? (
        <div className="card text-center py-16">
          <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
            <Calendar className="w-8 h-8 text-foreground-muted" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No Schedules Yet</h3>
          <p className="text-foreground-muted mb-6">
            Create schedules to automate server tasks like backups and restarts
          </p>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Create Schedule
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((schedule) => {
            const actionInfo = getActionInfo(schedule.action);
            const ActionIcon = actionInfo.icon;

            return (
              <div key={schedule.id} className={`card card-hover ${!schedule.enabled ? 'opacity-60' : ''}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      schedule.enabled ? 'bg-primary/20' : 'bg-secondary'
                    }`}>
                      <ActionIcon className={`w-5 h-5 ${schedule.enabled ? 'text-primary' : 'text-foreground-muted'}`} />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{actionInfo.name}</h3>
                        {!schedule.enabled && (
                          <span className="px-2 py-0.5 bg-foreground-muted/20 rounded text-xs text-foreground-muted">
                            Disabled
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-foreground-muted mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {describeCron(schedule.cron)}
                        </span>
                        {schedule.next_run && (
                          <span>Next: {formatDate(schedule.next_run)}</span>
                        )}
                      </div>
                      {schedule.action === 'command' && schedule.payload && (
                        <div className="text-xs text-foreground-muted mt-1 font-mono bg-secondary px-2 py-1 rounded inline-block">
                          {schedule.payload}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(schedule)}
                      className="btn btn-ghost btn-sm"
                      title={schedule.enabled ? 'Disable' : 'Enable'}
                    >
                      {schedule.enabled ? (
                        <ToggleRight className="w-5 h-5 text-primary" />
                      ) : (
                        <ToggleLeft className="w-5 h-5 text-foreground-muted" />
                      )}
                    </button>
                    <button
                      onClick={() => handleDelete(schedule.id)}
                      className="btn btn-ghost btn-sm text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Schedule Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Create Schedule</h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
                className="btn btn-ghost btn-sm p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              {/* Action Type */}
              <div>
                <label className="block text-sm font-medium mb-2">Action</label>
                <div className="grid grid-cols-2 gap-2">
                  {ACTION_TYPES.map((action) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.id}
                        type="button"
                        onClick={() => setFormAction(action.id)}
                        className={`p-3 rounded-lg border text-left transition-colors ${
                          formAction === action.id
                            ? 'border-primary bg-primary/10'
                            : 'border-card-border hover:border-primary/50'
                        }`}
                      >
                        <Icon className={`w-4 h-4 mb-1 ${formAction === action.id ? 'text-primary' : 'text-foreground-muted'}`} />
                        <div className="text-sm font-medium">{action.name}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Command payload for command action */}
              {formAction === 'command' && (
                <div>
                  <label className="block text-sm font-medium mb-2">Command</label>
                  <input
                    type="text"
                    value={formPayload}
                    onChange={(e) => setFormPayload(e.target.value)}
                    placeholder="say Hello, world!"
                    className="input font-mono"
                    required
                  />
                  <p className="text-xs text-foreground-muted mt-1">
                    Command to execute on the server console
                  </p>
                </div>
              )}

              {/* Cron Schedule */}
              <div>
                <label className="block text-sm font-medium mb-2">Schedule</label>
                <select
                  value={CRON_PRESETS.find((p) => p.cron === formCron) ? formCron : 'custom'}
                  onChange={(e) => {
                    if (e.target.value !== 'custom') {
                      setFormCron(e.target.value);
                    }
                  }}
                  className="input mb-2"
                >
                  {CRON_PRESETS.map((preset) => (
                    <option key={preset.cron} value={preset.cron}>
                      {preset.label}
                    </option>
                  ))}
                  <option value="custom">Custom cron expression</option>
                </select>
                <input
                  type="text"
                  value={formCron}
                  onChange={(e) => setFormCron(e.target.value)}
                  placeholder="0 0 * * *"
                  className="input font-mono"
                  required
                />
                <p className="text-xs text-foreground-muted mt-1">
                  Cron format: minute hour day month weekday
                </p>
              </div>

              {/* Enabled toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formEnabled}
                  onChange={(e) => setFormEnabled(e.target.checked)}
                  className="w-4 h-4 rounded bg-secondary border-card-border accent-primary"
                />
                <span>Enable schedule immediately</span>
              </label>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    resetForm();
                  }}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn btn-primary flex-1"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Create Schedule
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
