import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Loader2, RefreshCw } from 'lucide-react';

interface ServerType {
  id: string;
  name: string;
  description: string;
  supports_snapshots: boolean;
}

interface CreateServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateServerModal({ isOpen, onClose, onCreated }: CreateServerModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    type: 'paper',
    version: '',
    memory: '2G',
    port: 25565,
  });

  // Server types and versions state
  const [serverTypes, setServerTypes] = useState<ServerType[]>([]);
  const [versions, setVersions] = useState<string[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [includeSnapshots, setIncludeSnapshots] = useState(false);

  // Get current server type info
  const currentType = serverTypes.find((t) => t.id === form.type);
  const supportsSnapshots = currentType?.supports_snapshots ?? false;

  // Fetch server types on mount
  useEffect(() => {
    if (isOpen) {
      fetchServerTypes();
    }
  }, [isOpen]);

  // Reset snapshot toggle when switching to a type that doesn't support it
  useEffect(() => {
    if (!supportsSnapshots && includeSnapshots) {
      setIncludeSnapshots(false);
    }
  }, [form.type, supportsSnapshots, includeSnapshots]);

  const fetchServerTypes = async () => {
    try {
      const res = await fetch('/api/v1/server-types');
      if (res.ok) {
        const data = await res.json();
        setServerTypes(data);
      }
    } catch (e) {
      console.error('Failed to fetch server types:', e);
      // Fallback to default types
      setServerTypes([
        { id: 'paper', name: 'Paper', description: '', supports_snapshots: false },
        { id: 'vanilla', name: 'Vanilla', description: '', supports_snapshots: true },
        { id: 'fabric', name: 'Fabric', description: '', supports_snapshots: true },
        { id: 'purpur', name: 'Purpur', description: '', supports_snapshots: false },
      ]);
    }
  };

  const fetchVersions = useCallback(async (serverType: string, snapshots: boolean) => {
    setVersionsLoading(true);
    setError(null);

    try {
      const url = `/api/v1/versions/${serverType}?include_snapshots=${snapshots}`;
      const res = await fetch(url);

      if (res.ok) {
        const data = await res.json();
        const fetchedVersions = Array.isArray(data.versions) ? data.versions : [];
        setVersions(fetchedVersions);

        // Auto-select first version if none selected or current selection is invalid
        if (fetchedVersions.length > 0) {
          setForm((prev) => {
            if (!prev.version || !fetchedVersions.includes(prev.version)) {
              return { ...prev, version: fetchedVersions[0] };
            }
            return prev;
          });
        } else {
          setForm((prev) => ({ ...prev, version: '' }));
        }
      } else {
        setVersions([]);
        setForm((prev) => ({ ...prev, version: '' }));
        setError('Failed to fetch versions');
      }
    } catch (e) {
      console.error('Failed to fetch versions:', e);
      setVersions([]);
      setForm((prev) => ({ ...prev, version: '' }));
    } finally {
      setVersionsLoading(false);
    }
  }, []);

  // Fetch versions when type or snapshot toggle changes
  useEffect(() => {
    if (isOpen && form.type) {
      fetchVersions(form.type, includeSnapshots);
    }
  }, [isOpen, form.type, includeSnapshots, fetchVersions]);

  const handleTypeChange = (newType: string) => {
    setForm({ ...form, type: newType, version: '' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!form.version) {
      setError('Please select a version');
      setLoading(false);
      return;
    }

    try {
      const res = await fetch('/api/v1/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create server');
      }

      onCreated();
      onClose();
      setForm({ name: '', type: 'paper', version: '', memory: '2G', port: 25565 });
      setIncludeSnapshots(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onClose();
    setError(null);
    setForm({ name: '', type: 'paper', version: '', memory: '2G', port: 25565 });
    setIncludeSnapshots(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="card w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Create New Server</h2>
          <button onClick={handleClose} className="btn btn-ghost btn-sm p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-destructive/20 border border-destructive rounded-lg text-destructive text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">Server Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="My Minecraft Server"
              required
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Server Type</label>
            <select
              value={form.type}
              onChange={(e) => handleTypeChange(e.target.value)}
              className="input"
            >
              {serverTypes.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
            {currentType?.description && (
              <p className="text-xs text-foreground-muted mt-1">{currentType.description}</p>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">Version</label>
              {supportsSnapshots && (
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSnapshots}
                    onChange={(e) => setIncludeSnapshots(e.target.checked)}
                    className="w-4 h-4 rounded bg-secondary border-card-border accent-primary"
                  />
                  <span className="text-foreground-muted">Include Snapshots</span>
                </label>
              )}
            </div>
            <div className="relative">
              <select
                value={form.version}
                onChange={(e) => setForm({ ...form, version: e.target.value })}
                className="input"
                disabled={versionsLoading}
              >
                {versionsLoading ? (
                  <option>Loading versions...</option>
                ) : versions.length === 0 ? (
                  <option>No versions available</option>
                ) : (
                  versions.map((version) => (
                    <option key={version} value={version}>
                      {version}
                    </option>
                  ))
                )}
              </select>
              {versionsLoading && (
                <div className="absolute right-10 top-1/2 -translate-y-1/2">
                  <RefreshCw className="w-4 h-4 animate-spin text-foreground-muted" />
                </div>
              )}
            </div>
            <p className="text-xs text-foreground-muted mt-1">
              {versions.length} version{versions.length !== 1 ? 's' : ''} available
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Memory</label>
              <select
                value={form.memory}
                onChange={(e) => setForm({ ...form, memory: e.target.value })}
                className="input"
              >
                <option value="1G">1 GB</option>
                <option value="2G">2 GB</option>
                <option value="4G">4 GB</option>
                <option value="6G">6 GB</option>
                <option value="8G">8 GB</option>
                <option value="12G">12 GB</option>
                <option value="16G">16 GB</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Port</label>
              <input
                type="number"
                value={form.port}
                onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) })}
                min={1}
                max={65535}
                required
                className="input"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={handleClose} className="btn btn-secondary flex-1">
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || versionsLoading || !form.version}
              className="btn btn-primary flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Server
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
