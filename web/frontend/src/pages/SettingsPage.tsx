import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Save, RefreshCw, Loader2 } from 'lucide-react';
import { Server } from '../types';

interface SettingsPageProps {
  server: Server | null;
}

export function SettingsPage({ server }: SettingsPageProps) {
  const { id } = useParams<{ id: string }>();
  const serverId = parseInt(id || '0');

  const [properties, setProperties] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const fetchProperties = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/servers/${serverId}/properties`);
      if (res.ok) {
        const data = await res.json();
        setProperties(data);
      }
    } catch (e) {
      setError('Failed to load properties');
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const res = await fetch(`/api/v1/servers/${serverId}/properties`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ properties }),
      });

      if (!res.ok) throw new Error('Failed to save');

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      setError('Failed to save properties');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setProperties({ ...properties, [key]: value });
  };

  if (!server || server.id !== serverId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-foreground-muted">Server not found</p>
      </div>
    );
  }

  // Key properties to show prominently
  const keyProperties = [
    { key: 'server-port', label: 'Port', type: 'number' },
    { key: 'max-players', label: 'Max Players', type: 'number' },
    { key: 'motd', label: 'MOTD', type: 'text' },
    { key: 'difficulty', label: 'Difficulty', type: 'select', options: ['peaceful', 'easy', 'normal', 'hard'] },
    { key: 'gamemode', label: 'Gamemode', type: 'select', options: ['survival', 'creative', 'adventure', 'spectator'] },
    { key: 'pvp', label: 'PvP', type: 'boolean' },
    { key: 'online-mode', label: 'Online Mode', type: 'boolean' },
    { key: 'white-list', label: 'Whitelist', type: 'boolean' },
    { key: 'view-distance', label: 'View Distance', type: 'number' },
    { key: 'spawn-protection', label: 'Spawn Protection', type: 'number' },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">Server Settings</h2>
          <p className="text-foreground-muted text-sm mt-1">
            Edit server.properties configuration
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={fetchProperties} className="btn btn-ghost">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button onClick={handleSave} disabled={saving} className="btn btn-primary">
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-destructive/20 border border-destructive rounded-lg text-destructive text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-primary/20 border border-primary rounded-lg text-primary text-sm">
          Settings saved successfully!
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Key Properties Card */}
          <div className="card">
            <h3 className="font-semibold mb-4">General</h3>
            <div className="space-y-4">
              {keyProperties.map(({ key, label, type, options }) => (
                <div key={key}>
                  <label className="block text-sm font-medium mb-2">{label}</label>
                  {type === 'boolean' ? (
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={properties[key] === 'true'}
                        onChange={(e) => handleChange(key, e.target.checked ? 'true' : 'false')}
                        className="w-5 h-5 rounded border-card-border bg-background-secondary checked:bg-primary"
                      />
                      <span className="text-sm text-foreground-muted">
                        {properties[key] === 'true' ? 'Enabled' : 'Disabled'}
                      </span>
                    </label>
                  ) : type === 'select' ? (
                    <select
                      value={properties[key] || ''}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="input"
                    >
                      {options?.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={type}
                      value={properties[key] || ''}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="input"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* All Properties Card */}
          <div className="card">
            <h3 className="font-semibold mb-4">All Properties</h3>
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
              {Object.entries(properties)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-foreground-muted w-40 truncate" title={key}>
                      {key}
                    </span>
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="input text-sm py-1.5"
                    />
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
