import os
import shutil
import subprocess
import psutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    def get_java_path(self) -> Optional[str]:
        return shutil.which("java")

    def install_java(self, version: str = "temurin-17") -> bool:
        # Placeholder: On Windows, maybe use winget or scoop
        print("Java installation not implemented for Windows yet.")
        return False

    def start_process(self, cmd: List[str], cwd: Path, env: Dict[str, str]) -> subprocess.Popen:
        # Windows specific creation flags if needed (e.g. CREATE_NO_WINDOW)
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

    def stop_process(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return True
        except psutil.NoSuchProcess:
            return False

    def create_background_service(self, name: str, exec_cmd: str) -> bool:
        # Placeholder: Use NSSM or sc.exe
        return False

    def remove_background_service(self, name: str) -> bool:
        return False

    def open_firewall_port(self, port: int) -> bool:
        # Placeholder: netsh advfirewall firewall add rule ...
        return False

    def system_info(self) -> Dict[str, Any]:
        return {
            "platform": "windows",
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
        }

    def user_data_dir(self, app_name: str) -> Path:
        return Path(os.environ.get("APPDATA", "")) / app_name
