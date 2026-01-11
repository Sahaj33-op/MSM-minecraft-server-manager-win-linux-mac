import os
import shutil
import signal
import subprocess
import psutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import PlatformAdapter


class MacOSAdapter(PlatformAdapter):
    def get_java_path(self) -> Optional[str]:
        return shutil.which("java")

    def install_java(self, version: str = "temurin-17") -> bool:
        # Placeholder: Use brew
        return False

    def start_process(self, cmd: List[str], cwd: Path, env: Dict[str, str]) -> subprocess.Popen:
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid
        )

    def stop_process(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            # First try graceful SIGTERM
            os.kill(pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill with SIGKILL
                os.kill(pid, signal.SIGKILL)
                proc.wait(timeout=5)
            return True
        except psutil.NoSuchProcess:
            # Process already gone
            return True
        except ProcessLookupError:
            return True
        except Exception:
            return False

    def create_background_service(self, name: str, exec_cmd: str) -> bool:
        # Placeholder: Create launchd plist
        return False

    def remove_background_service(self, name: str) -> bool:
        return False

    def open_firewall_port(self, port: int) -> bool:
        return False

    def system_info(self) -> Dict[str, Any]:
        return {
            "platform": "macos",
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
        }

    def user_data_dir(self, app_name: str) -> Path:
        return Path.home() / "Library/Application Support" / app_name
