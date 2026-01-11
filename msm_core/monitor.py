import psutil
import platform
from typing import Dict, Any

def get_system_stats() -> Dict[str, Any]:
    memory = psutil.virtual_memory()
    # Use C: on Windows, / on Unix
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(disk_path)

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": memory.percent,
        "memory_used_gb": memory.used / (1024 ** 3),
        "memory_total_gb": memory.total / (1024 ** 3),
        "disk_percent": disk.percent,
        "disk_used_gb": disk.used / (1024 ** 3),
        "disk_total_gb": disk.total / (1024 ** 3),
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
