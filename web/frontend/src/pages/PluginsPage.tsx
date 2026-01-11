import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  Package,
  Search,
  Download,
  Trash2,
  AlertCircle,
  ExternalLink,
  ToggleLeft,
  ToggleRight,
  Loader2,
  ArrowUpCircle,
} from 'lucide-react';
import { Server } from '../types';

interface Plugin {
  id: number;
  server_id: number;
  name: string;
  filename: string;
  version: string | null;
  source: string;
  source_id: string | null;
  enabled: boolean;
  installed_at: string;
}

interface SearchResult {
  id: string;
  name: string;
  description: string;
  author: string;
  downloads: number;
  icon_url: string | null;
  url: string;
  versions?: string[];
}

interface PluginUpdate {
  plugin_id: number;
  name: string;
  current_version: string;
  latest_version: string;
  download_url: string;
}

interface PluginsPageProps {
  server: Server | null;
}

type TabType = 'installed' | 'modrinth' | 'hangar';

export function PluginsPage({ server }: PluginsPageProps) {
  const { id } = useParams<{ id: string }>();
  const serverId = id ? parseInt(id) : null;

  const [activeTab, setActiveTab] = useState<TabType>('installed');
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [updates, setUpdates] = useState<PluginUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [installing, setInstalling] = useState<string | null>(null);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchPlugins = useCallback(async () => {
    if (!serverId) return;

    try {
      setLoading(true);
      const res = await fetch(`/api/v1/servers/${serverId}/plugins`);
      if (res.ok) {
        const data = await res.json();
        setPlugins(Array.isArray(data) ? data : []);
        setError(null);
      } else {
        setError('Failed to fetch plugins');
      }
    } catch (e) {
      setError('Failed to fetch plugins');
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    if (activeTab === 'installed') {
      fetchPlugins();
    }
  }, [activeTab, fetchPlugins]);

  const handleSearch = async (source: 'modrinth' | 'hangar') => {
    if (!searchQuery.trim() || !server) return;

    setSearching(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        query: searchQuery,
        source,
        mc_version: server.version,
        limit: '20',
      });

      const res = await fetch(`/api/v1/plugins/search?${params}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(Array.isArray(data) ? data : []);
      } else {
        setError('Search failed');
        setSearchResults([]);
      }
    } catch (e) {
      setError('Search failed');
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleInstall = async (result: SearchResult, source: 'modrinth' | 'hangar') => {
    if (!serverId) return;

    setInstalling(result.id);
    setError(null);

    try {
      const res = await fetch(`/api/v1/servers/${serverId}/plugins`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source,
          project_id: result.id,
        }),
      });

      if (res.ok) {
        setActiveTab('installed');
        fetchPlugins();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to install plugin');
      }
    } catch (e) {
      setError('Failed to install plugin');
    } finally {
      setInstalling(null);
    }
  };

  const handleToggle = async (plugin: Plugin) => {
    try {
      const endpoint = plugin.enabled ? 'disable' : 'enable';
      const res = await fetch(`/api/v1/plugins/${plugin.id}/${endpoint}`, {
        method: 'POST',
      });

      if (res.ok) {
        fetchPlugins();
      } else {
        const data = await res.json();
        setError(data.detail || `Failed to ${endpoint} plugin`);
      }
    } catch (e) {
      setError('Failed to toggle plugin');
    }
  };

  const handleUninstall = async (pluginId: number) => {
    if (!confirm('Are you sure you want to uninstall this plugin?')) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/plugins/${pluginId}?delete_file=true`, {
        method: 'DELETE',
      });

      if (res.ok) {
        fetchPlugins();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to uninstall plugin');
      }
    } catch (e) {
      setError('Failed to uninstall plugin');
    }
  };

  const handleCheckUpdates = async () => {
    if (!serverId) return;

    setCheckingUpdates(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/servers/${serverId}/plugins/updates`);
      if (res.ok) {
        const data = await res.json();
        setUpdates(Array.isArray(data) ? data : []);
      } else {
        setError('Failed to check for updates');
      }
    } catch (e) {
      setError('Failed to check for updates');
    } finally {
      setCheckingUpdates(false);
    }
  };

  const formatDownloads = (count: number): string => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  if (!serverId) {
    return (
      <div className="p-6">
        <div className="card text-center py-12">
          <AlertCircle className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Server Selected</h3>
          <p className="text-foreground-muted">Select a server from the dashboard to manage plugins.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Plugins</h1>
          <p className="text-foreground-muted mt-1">
            {server?.name || `Server ${serverId}`} - {plugins.length} installed
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCheckUpdates}
            disabled={checkingUpdates}
            className="btn btn-ghost"
          >
            {checkingUpdates ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowUpCircle className="w-4 h-4" />
            )}
            Check Updates
          </button>
        </div>
      </div>

      {/* Updates Alert */}
      {updates.length > 0 && (
        <div className="mb-6 p-4 bg-primary/20 border border-primary rounded-lg">
          <div className="flex items-center gap-3">
            <ArrowUpCircle className="w-5 h-5 text-primary" />
            <span className="font-medium">{updates.length} update{updates.length !== 1 ? 's' : ''} available</span>
          </div>
          <div className="mt-2 space-y-1 text-sm text-foreground-muted">
            {updates.map((update) => (
              <div key={update.plugin_id}>
                {update.name}: {update.current_version} → {update.latest_version}
              </div>
            ))}
          </div>
        </div>
      )}

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

      {/* Tabs */}
      <div className="flex border-b border-card-border mb-6">
        <button
          onClick={() => setActiveTab('installed')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'installed'
              ? 'border-primary text-primary'
              : 'border-transparent text-foreground-muted hover:text-foreground'
          }`}
        >
          Installed
        </button>
        <button
          onClick={() => setActiveTab('modrinth')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'modrinth'
              ? 'border-primary text-primary'
              : 'border-transparent text-foreground-muted hover:text-foreground'
          }`}
        >
          Modrinth
        </button>
        <button
          onClick={() => setActiveTab('hangar')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'hangar'
              ? 'border-primary text-primary'
              : 'border-transparent text-foreground-muted hover:text-foreground'
          }`}
        >
          Hangar
        </button>
      </div>

      {/* Content */}
      {activeTab === 'installed' ? (
        loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-foreground-muted">Loading plugins...</p>
            </div>
          </div>
        ) : plugins.length === 0 ? (
          <div className="card text-center py-16">
            <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
              <Package className="w-8 h-8 text-foreground-muted" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Plugins Installed</h3>
            <p className="text-foreground-muted mb-6">
              Search Modrinth or Hangar to find and install plugins
            </p>
            <button onClick={() => setActiveTab('modrinth')} className="btn btn-primary">
              <Search className="w-4 h-4" />
              Browse Plugins
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {plugins.map((plugin) => (
              <div key={plugin.id} className="card card-hover">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-secondary rounded-lg flex items-center justify-center">
                      <Package className="w-5 h-5 text-primary" />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{plugin.name}</h3>
                        {plugin.version && (
                          <span className="px-2 py-0.5 bg-secondary rounded text-xs">
                            v{plugin.version}
                          </span>
                        )}
                        {!plugin.enabled && (
                          <span className="px-2 py-0.5 bg-foreground-muted/20 rounded text-xs text-foreground-muted">
                            Disabled
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-foreground-muted mt-1">
                        {plugin.filename} • {plugin.source}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(plugin)}
                      className="btn btn-ghost btn-sm"
                      title={plugin.enabled ? 'Disable' : 'Enable'}
                    >
                      {plugin.enabled ? (
                        <ToggleRight className="w-5 h-5 text-primary" />
                      ) : (
                        <ToggleLeft className="w-5 h-5 text-foreground-muted" />
                      )}
                    </button>
                    <button
                      onClick={() => handleUninstall(plugin.id)}
                      className="btn btn-ghost btn-sm text-destructive"
                      title="Uninstall"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <div>
          {/* Search Bar */}
          <div className="flex gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch(activeTab as 'modrinth' | 'hangar')}
                placeholder={`Search ${activeTab === 'modrinth' ? 'Modrinth' : 'Hangar'}...`}
                className="input pl-10"
              />
            </div>
            <button
              onClick={() => handleSearch(activeTab as 'modrinth' | 'hangar')}
              disabled={searching || !searchQuery.trim()}
              className="btn btn-primary"
            >
              {searching ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Search
            </button>
          </div>

          {/* Search Results */}
          {searching ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-foreground-muted">Searching...</p>
              </div>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="card text-center py-16">
              <Search className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Search for Plugins</h3>
              <p className="text-foreground-muted">
                Enter a search term to find plugins on {activeTab === 'modrinth' ? 'Modrinth' : 'Hangar'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {searchResults.map((result) => (
                <div key={result.id} className="card card-hover">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      {result.icon_url ? (
                        <img
                          src={result.icon_url}
                          alt={result.name}
                          className="w-12 h-12 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-secondary rounded-lg flex items-center justify-center">
                          <Package className="w-6 h-6 text-foreground-muted" />
                        </div>
                      )}

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{result.name}</h3>
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-foreground-muted hover:text-foreground"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                        <p className="text-sm text-foreground-muted mt-1 line-clamp-2">
                          {result.description}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-foreground-muted mt-2">
                          <span>by {result.author}</span>
                          <span>{formatDownloads(result.downloads)} downloads</span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleInstall(result, activeTab as 'modrinth' | 'hangar')}
                      disabled={installing === result.id}
                      className="btn btn-primary btn-sm shrink-0"
                    >
                      {installing === result.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      Install
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
