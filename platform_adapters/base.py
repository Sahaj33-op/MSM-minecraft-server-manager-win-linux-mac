from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific operations."""

    @abstractmethod
    def get_java_path(self) -> Optional[str]:
        """Return path to java executable."""
        raise NotImplementedError

    @abstractmethod
    def install_java(self, version: str = "temurin-17") -> bool:
        """Install Java."""
        raise NotImplementedError

    @abstractmethod
    def start_process(self, cmd: List[str], cwd: Path, env: Dict[str, str]) -> subprocess.Popen:
        """Start a process."""
        raise NotImplementedError

    @abstractmethod
    def stop_process(self, pid: int) -> bool:
        """Stop a process by PID."""
        raise NotImplementedError

    @abstractmethod
    def create_background_service(self, name: str, exec_cmd: str) -> bool:
        """Create a system service."""
        raise NotImplementedError

    @abstractmethod
    def remove_background_service(self, name: str) -> bool:
        """Remove a system service."""
        raise NotImplementedError

    @abstractmethod
    def open_firewall_port(self, port: int) -> bool:
        """Open a firewall port."""
        raise NotImplementedError

    @abstractmethod
    def system_info(self) -> Dict[str, Any]:
        """Return system info (cpu, memory, etc)."""
        raise NotImplementedError

    @abstractmethod
    def user_data_dir(self, app_name: str) -> Path:
        """Return user data directory."""
        raise NotImplementedError
