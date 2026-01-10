"""Platform detection utilities.

This module is intentionally standalone with no dependencies on other MSM modules
to avoid circular imports between msm_core and platform_adapters.
"""
import platform


def get_os_name() -> str:
    """Return normalized OS name: 'windows', 'linux', or 'macos'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def get_arch() -> str:
    """Return normalized architecture: 'x64', 'arm64', etc."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    elif machine in ("i386", "i686", "x86"):
        return "x86"
    return machine


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_os_name() == "windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_os_name() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_os_name() == "macos"
