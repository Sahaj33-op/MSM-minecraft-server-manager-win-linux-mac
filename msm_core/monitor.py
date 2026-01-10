import psutil
from typing import Dict, Any

def get_system_stats() -> Dict[str, Any]:
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage("/").percent
    }

def get_process_stats(pid: int) -> Dict[str, Any]:
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                "cpu_percent": proc.cpu_percent(),
                "memory_info": proc.memory_info().rss,
                "status": proc.status()
            }
    except psutil.NoSuchProcess:
        return {}
