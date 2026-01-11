// Types for the MSM frontend

export interface Server {
  id: number;
  name: string;
  type: string;
  version: string;
  path: string;
  port: number;
  memory: string;
  is_running: boolean;
  pid: number | null;
  java_path: string | null;
  jvm_args: string | null;
  created_at: string | null;
}

export interface ServerStatus {
  id: number;
  name: string;
  is_running: boolean;
  pid: number | null;
  uptime: number | null;
  cpu_percent: number | null;
  memory_mb: number | null;
  player_count: number | null;
}

export interface Backup {
  id: number;
  server_id: number;
  server_name: string;
  filename: string;
  size_bytes: number;
  backup_type: string;
  created_at: string;
}

export interface Plugin {
  id: number;
  server_id: number;
  name: string;
  filename: string;
  source: string;
  project_id: string | null;
  version: string | null;
  enabled: boolean;
  installed_at: string;
}

export interface Schedule {
  id: number;
  server_id: number;
  server_name: string;
  action: string;
  cron_expression: string;
  payload: string | null;
  enabled: boolean;
  last_run: string | null;
  next_run: string | null;
}

export interface ConsoleMessage {
  type: 'output' | 'command_ack' | 'error' | 'history' | 'heartbeat' | 'server_stopped' | 'pong';
  data?: {
    timestamp: string;
    stream: string;
    line: string;
  };
  lines?: Array<{ timestamp: string; stream: string; line: string } | string>;
  success?: boolean;
  command?: string;
  message?: string;
  exit_code?: number;
}

export interface SystemStats {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
}
