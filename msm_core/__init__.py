"""
MSM Core Module - Minecraft Server Manager Core Library.
"""
__version__ = "0.1.0"

from .exceptions import (
    MSMError,
    ServerNotFoundError,
    ServerAlreadyExistsError,
    ServerAlreadyRunningError,
    ServerNotRunningError,
    JavaNotFoundError,
    DownloadError,
    ChecksumError,
    ValidationError,
    UnsupportedServerTypeError,
    InstallationError,
)
from .db import get_db, get_session, Server, Backup
from .config import get_config, get_config_manager
from .console import get_console_manager
from . import api
from . import lifecycle
from . import installers

__all__ = [
    "__version__",
    # Exceptions
    "MSMError",
    "ServerNotFoundError",
    "ServerAlreadyExistsError",
    "ServerAlreadyRunningError",
    "ServerNotRunningError",
    "JavaNotFoundError",
    "DownloadError",
    "ChecksumError",
    "ValidationError",
    "UnsupportedServerTypeError",
    "InstallationError",
    # Database
    "get_db",
    "get_session",
    "Server",
    "Backup",
    # Config
    "get_config",
    "get_config_manager",
    # Console
    "get_console_manager",
    # Submodules
    "api",
    "lifecycle",
    "installers",
]
