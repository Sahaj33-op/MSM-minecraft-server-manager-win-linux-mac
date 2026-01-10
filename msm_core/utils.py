"""Utility functions for MSM."""
import hashlib
import re
from pathlib import Path

# Re-export from platform module for backwards compatibility
from msm_core.platform import get_os_name, get_arch, is_windows, is_linux, is_macos

from .exceptions import ValidationError


# Server name validation pattern: alphanumeric, underscore, hyphen
SERVER_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
MAX_SERVER_NAME_LENGTH = 64


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal string of the SHA256 hash.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(8192), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_sha512(file_path: Path) -> str:
    """Calculate SHA512 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal string of the SHA512 hash.
    """
    sha512_hash = hashlib.sha512()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(8192), b""):
            sha512_hash.update(byte_block)
    return sha512_hash.hexdigest()


def resolve_path(path_str: str) -> Path:
    """Resolve path with user expansion.

    Args:
        path_str: Path string that may contain ~ or relative paths.

    Returns:
        Resolved absolute Path object.
    """
    return Path(path_str).expanduser().resolve()


def validate_server_name(name: str) -> str:
    """Validate and normalize a server name.

    Args:
        name: The server name to validate.

    Returns:
        The validated server name.

    Raises:
        ValidationError: If the name is invalid.
    """
    if not name:
        raise ValidationError("name", "Server name cannot be empty")

    if len(name) > MAX_SERVER_NAME_LENGTH:
        raise ValidationError("name", f"Server name cannot exceed {MAX_SERVER_NAME_LENGTH} characters")

    if not SERVER_NAME_PATTERN.match(name):
        raise ValidationError(
            "name",
            "Server name must start with a letter and contain only letters, numbers, underscores, and hyphens"
        )

    # Check for path traversal attempts
    if ".." in name or "/" in name or "\\" in name:
        raise ValidationError("name", "Server name cannot contain path separators")

    return name


def validate_port(port: int) -> int:
    """Validate a port number.

    Args:
        port: The port number to validate.

    Returns:
        The validated port number.

    Raises:
        ValidationError: If the port is invalid.
    """
    if not isinstance(port, int):
        raise ValidationError("port", "Port must be an integer")

    if port < 1 or port > 65535:
        raise ValidationError("port", "Port must be between 1 and 65535")

    if port < 1024:
        raise ValidationError("port", "Port must be 1024 or higher (ports below 1024 require root)")

    return port


def validate_memory(memory: str) -> str:
    """Validate a memory allocation string.

    Args:
        memory: Memory string like "2G", "512M", "4096M".

    Returns:
        The validated memory string.

    Raises:
        ValidationError: If the memory string is invalid.
    """
    if not memory:
        raise ValidationError("memory", "Memory allocation cannot be empty")

    memory = memory.upper()

    # Pattern: number followed by M or G
    pattern = re.compile(r'^(\d+)([MG])$')
    match = pattern.match(memory)

    if not match:
        raise ValidationError("memory", "Memory must be specified as a number followed by M or G (e.g., '2G', '512M')")

    value = int(match.group(1))
    unit = match.group(2)

    # Convert to MB for validation
    mb_value = value * 1024 if unit == "G" else value

    if mb_value < 512:
        raise ValidationError("memory", "Memory allocation must be at least 512M")

    if mb_value > 64 * 1024:  # 64GB max
        raise ValidationError("memory", "Memory allocation cannot exceed 64G")

    return memory


def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable string like "1.5 GB", "256 MB".
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
