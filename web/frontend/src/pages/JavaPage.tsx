import { useState, useEffect } from 'react';
import {
  Coffee,
  Download,
  Trash2,
  AlertCircle,
  RefreshCw,
  Check,
  Loader2,
  HardDrive,
  ExternalLink,
} from 'lucide-react';

interface JavaInstallation {
  path: string;
  version: string;
  major_version: number;
  vendor: string;
  is_jdk: boolean;
  managed: boolean;
}

interface AvailableJava {
  version: number;
  lts: boolean;
  download_url: string;
  filename: string;
}

type TabType = 'installed' | 'available';

export function JavaPage() {
  const [activeTab, setActiveTab] = useState<TabType>('installed');
  const [installed, setInstalled] = useState<JavaInstallation[]>([]);
  const [_managed, setManaged] = useState<JavaInstallation[]>([]);
  const [available, setAvailable] = useState<AvailableJava[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recommendedVersion, setRecommendedVersion] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'installed') {
      fetchInstalled();
    } else {
      fetchAvailable();
    }
  }, [activeTab]);

  const fetchInstalled = async () => {
    setLoading(true);
    setError(null);

    try {
      const [installedRes, managedRes] = await Promise.all([
        fetch('/api/v1/java/installed'),
        fetch('/api/v1/java/managed'),
      ]);

      if (installedRes.ok) {
        const data = await installedRes.json();
        setInstalled(Array.isArray(data) ? data : []);
      }

      if (managedRes.ok) {
        const data = await managedRes.json();
        setManaged(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setError('Failed to fetch Java installations');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailable = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/v1/java/available');
      if (res.ok) {
        const data = await res.json();
        setAvailable(Array.isArray(data) ? data : []);
      } else {
        setError('Failed to fetch available Java versions');
      }
    } catch (e) {
      setError('Failed to fetch available Java versions');
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (version: number) => {
    setInstalling(version);
    setError(null);

    try {
      const res = await fetch(`/api/v1/java/install/${version}`, {
        method: 'POST',
      });

      if (res.ok) {
        setActiveTab('installed');
        fetchInstalled();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to install Java');
      }
    } catch (e) {
      setError('Failed to install Java');
    } finally {
      setInstalling(null);
    }
  };

  const checkRecommended = async (mcVersion: string) => {
    try {
      const res = await fetch(`/api/v1/java/recommend/${mcVersion}`);
      if (res.ok) {
        const data = await res.json();
        if (data.recommended) {
          setRecommendedVersion(`Java ${data.recommended.major_version} recommended for MC ${mcVersion}`);
        } else {
          setRecommendedVersion(data.message || 'No compatible Java found');
        }
      }
    } catch (e) {
      console.error('Failed to check recommended Java');
    }
  };

  const isAlreadyInstalled = (version: number): boolean => {
    return installed.some((j) => j.major_version === version);
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Java Runtime</h1>
          <p className="text-foreground-muted mt-1">
            Manage Java installations for running Minecraft servers
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => activeTab === 'installed' ? fetchInstalled() : fetchAvailable()}
            className="btn btn-ghost"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
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

      {/* Recommendation Checker */}
      <div className="card mb-6">
        <h3 className="font-medium mb-3">Check Recommended Java</h3>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Enter Minecraft version (e.g., 1.20.4)"
            className="input flex-1"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                checkRecommended((e.target as HTMLInputElement).value);
              }
            }}
          />
          <button
            onClick={(e) => {
              const input = (e.currentTarget.previousElementSibling as HTMLInputElement);
              checkRecommended(input.value);
            }}
            className="btn btn-secondary"
          >
            Check
          </button>
        </div>
        {recommendedVersion && (
          <p className="text-sm text-primary mt-2">{recommendedVersion}</p>
        )}
      </div>

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
          Installed ({installed.length})
        </button>
        <button
          onClick={() => setActiveTab('available')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'available'
              ? 'border-primary text-primary'
              : 'border-transparent text-foreground-muted hover:text-foreground'
          }`}
        >
          Available
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-foreground-muted">Loading...</p>
          </div>
        </div>
      ) : activeTab === 'installed' ? (
        installed.length === 0 ? (
          <div className="card text-center py-16">
            <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
              <Coffee className="w-8 h-8 text-foreground-muted" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Java Found</h3>
            <p className="text-foreground-muted mb-6">
              Install Java from the Available tab to run Minecraft servers
            </p>
            <button onClick={() => setActiveTab('available')} className="btn btn-primary">
              <Download className="w-4 h-4" />
              Browse Available Versions
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {installed.map((java, index) => (
              <div key={index} className="card card-hover">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      java.managed ? 'bg-primary/20' : 'bg-secondary'
                    }`}>
                      <Coffee className={`w-5 h-5 ${java.managed ? 'text-primary' : 'text-foreground-muted'}`} />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">Java {java.major_version}</h3>
                        {java.is_jdk && (
                          <span className="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs">
                            JDK
                          </span>
                        )}
                        {java.managed && (
                          <span className="px-2 py-0.5 bg-secondary rounded text-xs">
                            MSM Managed
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-foreground-muted mt-1">
                        {java.vendor} • {java.version}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-foreground-muted mt-1">
                        <HardDrive className="w-3 h-3" />
                        <span className="font-mono truncate max-w-md">{java.path}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {java.managed && (
                      <button
                        className="btn btn-ghost btn-sm text-destructive"
                        title="Remove"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Java Version Compatibility Info */}
            <div className="card bg-secondary/50 mt-6">
              <h4 className="font-medium mb-2">Minecraft Java Compatibility</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-foreground-muted">MC 1.20.5+</div>
                  <div className="font-medium">Java 21</div>
                </div>
                <div>
                  <div className="text-foreground-muted">MC 1.18 - 1.20.4</div>
                  <div className="font-medium">Java 17</div>
                </div>
                <div>
                  <div className="text-foreground-muted">MC 1.17</div>
                  <div className="font-medium">Java 16+</div>
                </div>
                <div>
                  <div className="text-foreground-muted">MC 1.12 - 1.16</div>
                  <div className="font-medium">Java 8</div>
                </div>
              </div>
            </div>
          </div>
        )
      ) : (
        <div className="space-y-3">
          {available.length === 0 ? (
            <div className="card text-center py-16">
              <AlertCircle className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Could Not Fetch Versions</h3>
              <p className="text-foreground-muted">
                Unable to fetch available Java versions. Please check your internet connection.
              </p>
            </div>
          ) : (
            available.map((java) => {
              const alreadyInstalled = isAlreadyInstalled(java.version);

              return (
                <div key={java.version} className="card card-hover">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-secondary rounded-lg flex items-center justify-center">
                        <Coffee className="w-5 h-5 text-foreground-muted" />
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">Java {java.version}</h3>
                          {java.lts && (
                            <span className="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs">
                              LTS
                            </span>
                          )}
                          {alreadyInstalled && (
                            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs flex items-center gap-1">
                              <Check className="w-3 h-3" />
                              Installed
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-foreground-muted mt-1">
                          Eclipse Temurin (Adoptium) • {java.filename}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <a
                        href={`https://adoptium.net/temurin/releases/?version=${java.version}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-ghost btn-sm"
                        title="View on Adoptium"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                      <button
                        onClick={() => handleInstall(java.version)}
                        disabled={installing === java.version || alreadyInstalled}
                        className="btn btn-primary btn-sm"
                      >
                        {installing === java.version ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Installing...
                          </>
                        ) : alreadyInstalled ? (
                          <>
                            <Check className="w-4 h-4" />
                            Installed
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4" />
                            Install
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {/* Info about Adoptium */}
          <div className="card bg-secondary/50 mt-6">
            <div className="flex items-start gap-3">
              <Coffee className="w-5 h-5 text-primary mt-0.5" />
              <div>
                <h4 className="font-medium mb-1">About Eclipse Temurin</h4>
                <p className="text-sm text-foreground-muted">
                  Eclipse Temurin is the open source Java runtime from Adoptium.
                  It's free, well-tested, and recommended for running Minecraft servers.
                  LTS (Long Term Support) versions receive updates for several years.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
