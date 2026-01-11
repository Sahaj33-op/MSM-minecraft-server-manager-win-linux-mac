import { useState, useEffect, useRef, useCallback } from 'react';
import { ConsoleMessage, Server, SystemStats } from '../types';

// Constants for retry logic
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_MS = 2000;
const API_RETRY_ATTEMPTS = 3;
const API_RETRY_DELAY_MS = 1000;

// Helper function for retrying API calls
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retries: number = API_RETRY_ATTEMPTS
): Promise<Response> {
  let lastError: Error | null = null;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (res.ok || res.status < 500) {
        return res;
      }
      // Server error, retry
      lastError = new Error(`Server error: ${res.status}`);
    } catch (e) {
      lastError = e instanceof Error ? e : new Error('Network error');
    }
    if (i < retries - 1) {
      await new Promise(resolve => setTimeout(resolve, API_RETRY_DELAY_MS * (i + 1)));
    }
  }
  throw lastError || new Error('Request failed after retries');
}

export function useConsoleWebSocket(serverId: number | null) {
  const [messages, setMessages] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [serverStopped, setServerStopped] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (!serverId) return;

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`ws://${window.location.host}/api/v1/servers/${serverId}/console/ws`);
    wsRef.current = ws;
    intentionalCloseRef.current = false;

    ws.onopen = () => {
      setConnected(true);
      setReconnectAttempt(0);
      setServerStopped(false);
    };

    ws.onmessage = (event) => {
      try {
        const msg: ConsoleMessage = JSON.parse(event.data);

        if (msg.type === 'history' && msg.lines) {
          type LineEntry = { timestamp: string; stream: string; line: string } | string;
          const lines = Array.isArray(msg.lines)
            ? msg.lines.map((entry: LineEntry) => {
                if (typeof entry === 'string') return entry;
                if (entry && typeof entry === 'object' && entry.line) {
                  return `[${entry.timestamp || ''}] ${entry.line}`;
                }
                return String(entry);
              })
            : [];
          setMessages(lines);
        } else if (msg.type === 'output' && msg.data) {
          const entry = msg.data;
          const line = typeof entry === 'object' && entry.line
            ? `[${entry.timestamp || ''}] ${entry.line}`
            : String(entry);
          setMessages(prev => [...prev, line]);
        } else if (msg.type === 'command_ack') {
          // Command acknowledged
        } else if (msg.type === 'error' && msg.message) {
          setMessages(prev => [...prev, `[ERROR] ${msg.message}`]);
        } else if (msg.type === 'server_stopped') {
          // Server process has stopped
          setServerStopped(true);
          const exitMsg = `[MSM] Server stopped with exit code ${msg.exit_code ?? 'unknown'}`;
          setMessages(prev => [...prev, exitMsg]);
        } else if (msg.type === 'heartbeat') {
          // Heartbeat received - connection is alive
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);

      // Auto-reconnect if not intentionally closed and within retry limit
      if (!intentionalCloseRef.current && reconnectAttempt < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAY_MS * Math.pow(1.5, reconnectAttempt);
        reconnectTimeoutRef.current = setTimeout(() => {
          setReconnectAttempt(prev => prev + 1);
          connect();
        }, delay);
      }
    };

    ws.onerror = () => {
      // onclose will be called after onerror
    };

    return () => {
      intentionalCloseRef.current = true;
      ws.close();
    };
  }, [serverId, reconnectAttempt]);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'command', command }));
    }
  }, []);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const reconnect = useCallback(() => {
    setReconnectAttempt(0);
    connect();
  }, [connect]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup?.();
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    connected,
    serverStopped,
    reconnectAttempt,
    sendCommand,
    disconnect,
    reconnect
  };
}

export function useServers() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);

  const fetchServers = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchWithRetry('/api/v1/servers');
      if (!res.ok) throw new Error('Failed to fetch servers');
      const data = await res.json();
      setServers(Array.isArray(data) ? data : []);
      setError(null);
      setLastFetchTime(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      // Keep existing servers on error to avoid UI flicker
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServers();
    const interval = setInterval(fetchServers, 5000);
    return () => clearInterval(interval);
  }, [fetchServers]);

  return { servers, loading, error, lastFetchTime, refetch: fetchServers };
}

export function useSystemStats() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetchWithRetry('/api/v1/stats');
        if (res.ok) {
          const data = await res.json();
          setStats(data);
          setError(null);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to fetch stats');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  return { stats, loading, error };
}

// Health check hook for monitoring API connectivity
export function useApiHealth() {
  const [healthy, setHealthy] = useState(true);
  const [checking, setChecking] = useState(false);
  const [lastCheck, setLastCheck] = useState<number>(0);
  const [uptimeSeconds, setUptimeSeconds] = useState<number | null>(null);

  const checkHealth = useCallback(async () => {
    setChecking(true);
    try {
      const res = await fetch('/api/v1/health', { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        setHealthy(data.status === 'healthy' || data.status === 'degraded');
        setUptimeSeconds(data.uptime_seconds);
      } else {
        setHealthy(false);
      }
    } catch {
      setHealthy(false);
    } finally {
      setChecking(false);
      setLastCheck(Date.now());
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [checkHealth]);

  return { healthy, checking, lastCheck, uptimeSeconds, checkHealth };
}
