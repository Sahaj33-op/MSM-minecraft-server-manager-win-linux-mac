import { Cpu, HardDrive, MemoryStick, Activity } from 'lucide-react';

interface StatsBarProps {
  stats: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_gb: number;
    memory_total_gb: number;
    disk_percent: number;
    disk_used_gb: number;
    disk_total_gb: number;
  } | null;
}

export function StatsBar({ stats }: StatsBarProps) {
  if (!stats) {
    return (
      <div className="stats-bar px-5 py-2.5">
        <div className="flex items-center gap-2 text-foreground-muted text-xs">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span>Loading system stats...</span>
        </div>
      </div>
    );
  }

  const getColorClass = (percent: number) => {
    if (percent >= 90) return 'bg-destructive';
    if (percent >= 70) return 'bg-accent';
    return 'bg-primary';
  };

  const getGlowClass = (percent: number) => {
    if (percent >= 90) return 'shadow-[0_0_8px_rgba(239,68,68,0.3)]';
    if (percent >= 70) return 'shadow-[0_0_8px_rgba(245,158,11,0.3)]';
    return '';
  };

  return (
    <div className="stats-bar px-5 py-2.5">
      <div className="flex items-center gap-6">
        {/* CPU */}
        <div className="flex items-center gap-2.5">
          <Cpu className="w-3.5 h-3.5 text-foreground-muted" />
          <div className="w-28">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-foreground-muted">CPU</span>
              <span className="font-medium tabular-nums">{stats.cpu_percent.toFixed(0)}%</span>
            </div>
            <div className="h-1 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full ${getColorClass(stats.cpu_percent)} ${getGlowClass(stats.cpu_percent)} transition-all duration-500 ease-out rounded-full`}
                style={{ width: `${Math.min(stats.cpu_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="w-px h-6 bg-card-border" />

        {/* Memory */}
        <div className="flex items-center gap-2.5">
          <MemoryStick className="w-3.5 h-3.5 text-foreground-muted" />
          <div className="w-28">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-foreground-muted">RAM</span>
              <span className="font-medium tabular-nums">
                {stats.memory_used_gb.toFixed(1)}<span className="text-foreground-muted">/{stats.memory_total_gb.toFixed(0)}G</span>
              </span>
            </div>
            <div className="h-1 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full ${getColorClass(stats.memory_percent)} ${getGlowClass(stats.memory_percent)} transition-all duration-500 ease-out rounded-full`}
                style={{ width: `${Math.min(stats.memory_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="w-px h-6 bg-card-border" />

        {/* Disk */}
        <div className="flex items-center gap-2.5">
          <HardDrive className="w-3.5 h-3.5 text-foreground-muted" />
          <div className="w-28">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-foreground-muted">Disk</span>
              <span className="font-medium tabular-nums">
                {stats.disk_used_gb.toFixed(0)}<span className="text-foreground-muted">/{stats.disk_total_gb.toFixed(0)}G</span>
              </span>
            </div>
            <div className="h-1 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full ${getColorClass(stats.disk_percent)} ${getGlowClass(stats.disk_percent)} transition-all duration-500 ease-out rounded-full`}
                style={{ width: `${Math.min(stats.disk_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
