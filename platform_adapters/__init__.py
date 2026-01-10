"""Platform adapters for OS-specific operations."""
from typing import Optional

from .base import PlatformAdapter
from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter
from msm_core.platform import get_os_name

# Singleton adapter instance
_adapter_instance: Optional[PlatformAdapter] = None


def get_adapter() -> PlatformAdapter:
    """Get the platform adapter for the current OS (singleton)."""
    global _adapter_instance
    if _adapter_instance is None:
        os_name = get_os_name()
        if os_name == "windows":
            _adapter_instance = WindowsAdapter()
        elif os_name == "linux":
            _adapter_instance = LinuxAdapter()
        elif os_name == "macos":
            _adapter_instance = MacOSAdapter()
        else:
            raise NotImplementedError(f"OS '{os_name}' is not supported")
    return _adapter_instance


def reset_adapter() -> None:
    """Reset the adapter singleton. Useful for testing."""
    global _adapter_instance
    _adapter_instance = None


__all__ = [
    "PlatformAdapter",
    "WindowsAdapter",
    "LinuxAdapter",
    "MacOSAdapter",
    "get_adapter",
    "reset_adapter",
]
