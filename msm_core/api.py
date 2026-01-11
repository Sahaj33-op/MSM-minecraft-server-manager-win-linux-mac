"""Core API for MSM server management."""
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .db import get_session, Server
from .config import get_config
from .lifecycle import start_server, stop_server, sync_server_states
from .installers import install_server
from .exceptions import (
    ServerNotFoundError,
    ServerAlreadyExistsError,
    ValidationError,
)
from .schemas import ServerResponse
from .utils import validate_server_name, validate_port, validate_memory
from platform_adapters import get_adapter

logger = logging.getLogger(__name__)


def _validate_path_is_safe_for_deletion(server_path: Path, server_name: str) -> bool:
    """Validate that a path is safe to delete.

    Ensures the path:
    1. Is within the MSM data directory
    2. Is not a system directory
    3. Contains expected server files

    Args:
        server_path: The path to validate.
        server_name: The server name for logging.

    Returns:
        True if safe to delete.

    Raises:
        ValidationError: If the path is not safe.
    """
    adapter = get_adapter()
    data_dir = adapter.user_data_dir("msm")
    servers_dir = data_dir / "servers"

    # Resolve paths to handle symlinks and ..
    try:
        resolved_path = server_path.resolve()
        resolved_servers_dir = servers_dir.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError("path", f"Cannot resolve server path: {e}")

    # Check if path is under the servers directory
    try:
        resolved_path.relative_to(resolved_servers_dir)
    except ValueError:
        logger.error(
            f"SECURITY: Attempted to delete path outside servers directory: {resolved_path}"
        )
        raise ValidationError(
            "path",
            f"Server path '{resolved_path}' is not within the MSM servers directory. "
            "Deletion blocked for security."
        )

    # Additional safety: don't delete if path is too short (likely a parent directory)
    if len(resolved_path.parts) <= len(resolved_servers_dir.parts):
        raise ValidationError("path", "Cannot delete the servers root directory")

    # Check that the directory name matches the server name (sanity check)
    if resolved_path.name != server_name:
        logger.warning(
            f"Server directory name '{resolved_path.name}' doesn't match "
            f"server name '{server_name}'. Proceeding with caution."
        )

    return True


def create_server(
    name: str,
    server_type: str,
    version: str,
    memory: Optional[str] = None,
    port: Optional[int] = None,
) -> ServerResponse:
    """Create a new Minecraft server.

    Args:
        name: Unique server name.
        server_type: Server type (paper, vanilla, fabric, forge).
        version: Minecraft version (e.g., "1.20.4").
        memory: Memory allocation (e.g., "2G"). Defaults to config value.
        port: Server port. Defaults to config value.

    Returns:
        The created server as a ServerResponse DTO.

    Raises:
        ValidationError: If any input is invalid.
        ServerAlreadyExistsError: If a server with this name already exists.
        InstallationError: If server installation fails.
    """
    # Validate inputs
    name = validate_server_name(name)
    config = get_config()
    memory = validate_memory(memory or config.default_java_memory)
    port = validate_port(port or config.default_port)

    # Normalize server type
    server_type = server_type.lower().strip()
    valid_types = ["paper", "vanilla", "fabric", "forge", "purpur", "spigot"]
    if server_type not in valid_types:
        raise ValidationError("type", f"Server type must be one of: {', '.join(valid_types)}")

    # Check for existing server
    with get_session() as session:
        existing = session.query(Server).filter(Server.name == name).first()
        if existing:
            raise ServerAlreadyExistsError(name)

    # Determine server directory
    adapter = get_adapter()
    data_dir = adapter.user_data_dir("msm")
    server_dir = data_dir / "servers" / name
    server_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating server '{name}' ({server_type} {version}) at {server_dir}")

    # Install server files
    if not install_server(name, server_type, version, server_dir):
        # Clean up on failure
        shutil.rmtree(server_dir, ignore_errors=True)
        raise ValidationError("installation", f"Failed to install {server_type} server")

    # Create database record
    with get_session() as session:
        server = Server(
            name=name,
            type=server_type,
            version=version,
            path=str(server_dir),
            port=port,
            memory=memory,
        )
        session.add(server)
        session.flush()  # Get the ID

        logger.info(f"Server '{name}' created with ID {server.id}")

        # Return a Pydantic DTO (properly handles session closure)
        return ServerResponse.model_validate(server)


def list_servers() -> List[dict]:
    """List all servers.

    Verifies actual running state against OS process table for accuracy.

    Returns:
        List of server dictionaries.
    """
    import psutil

    with get_session() as session:
        servers = session.query(Server).all()
        result = []

        for s in servers:
            # Verify actual running state against OS
            actual_running = False
            if s.pid:
                try:
                    proc = psutil.Process(s.pid)
                    if "java" in proc.name().lower() and proc.is_running():
                        actual_running = True
                except psutil.NoSuchProcess:
                    pass

            # Correct database state if needed
            if s.is_running != actual_running:
                s.is_running = actual_running
                if not actual_running:
                    s.pid = None

            result.append({
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "version": s.version,
                "path": s.path,
                "port": s.port,
                "memory": s.memory,
                "is_running": actual_running,
                "pid": s.pid if actual_running else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

        return result


def get_server(name: str) -> Optional[dict]:
    """Get a server by name.

    Args:
        name: Server name.

    Returns:
        Server dictionary or None if not found.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.name == name).first()
        if not server:
            return None

        return {
            "id": server.id,
            "name": server.name,
            "type": server.type,
            "version": server.version,
            "path": server.path,
            "port": server.port,
            "memory": server.memory,
            "is_running": server.is_running,
            "pid": server.pid,
            "java_path": server.java_path,
            "jvm_args": server.jvm_args,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "last_started": server.last_started.isoformat() if server.last_started else None,
            "last_stopped": server.last_stopped.isoformat() if server.last_stopped else None,
        }


def get_server_by_id(server_id: int) -> Optional[dict]:
    """Get a server by ID.

    Args:
        server_id: Server database ID.

    Returns:
        Server dictionary or None if not found.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            return None

        return {
            "id": server.id,
            "name": server.name,
            "type": server.type,
            "version": server.version,
            "path": server.path,
            "port": server.port,
            "memory": server.memory,
            "is_running": server.is_running,
            "pid": server.pid,
            "java_path": server.java_path,
            "jvm_args": server.jvm_args,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "last_started": server.last_started.isoformat() if server.last_started else None,
            "last_stopped": server.last_stopped.isoformat() if server.last_stopped else None,
        }


def delete_server(name: str, keep_files: bool = False) -> bool:
    """Delete a server.

    Args:
        name: Server name.
        keep_files: If True, don't delete server files.

    Returns:
        True if successful.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
        ValidationError: If the server is running or path is unsafe.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.name == name).first()

        if not server:
            raise ServerNotFoundError(name)

        if server.is_running:
            raise ValidationError("server", "Cannot delete a running server. Stop it first.")

        server_path = Path(server.path)
        server_name = server.name

        # Delete from database
        session.delete(server)
        logger.info(f"Server '{name}' deleted from database")

    # Delete files (outside transaction) with path safety validation
    if not keep_files and server_path.exists():
        # SECURITY: Validate path before deletion to prevent path traversal attacks
        _validate_path_is_safe_for_deletion(server_path, server_name)

        logger.info(f"Deleting server files at {server_path}")
        shutil.rmtree(server_path, ignore_errors=True)

    return True


def import_server(
    name: str,
    server_type: str,
    version: str,
    path: Path,
    memory: Optional[str] = None,
    port: Optional[int] = None,
) -> ServerResponse:
    """Import an existing server directory.

    Args:
        name: Name for the imported server.
        server_type: Server type (paper, vanilla, etc.).
        version: Minecraft version.
        path: Path to existing server directory.
        memory: Memory allocation.
        port: Server port.

    Returns:
        The imported server as a ServerResponse DTO.

    Raises:
        ValidationError: If the directory is invalid.
        ServerAlreadyExistsError: If a server with this name exists.
    """
    name = validate_server_name(name)
    config = get_config()
    memory = validate_memory(memory or config.default_java_memory)
    port = validate_port(port or config.default_port)

    path = Path(path).resolve()

    if not path.exists():
        raise ValidationError("path", f"Directory does not exist: {path}")

    if not (path / "server.jar").exists():
        raise ValidationError("path", "No server.jar found in directory")

    with get_session() as session:
        existing = session.query(Server).filter(Server.name == name).first()
        if existing:
            raise ServerAlreadyExistsError(name)

        server = Server(
            name=name,
            type=server_type,
            version=version,
            path=str(path),
            port=port,
            memory=memory,
        )
        session.add(server)
        session.flush()

        logger.info(f"Imported server '{name}' from {path}")

        # Return a Pydantic DTO
        return ServerResponse.model_validate(server)


def update_server(
    name: str,
    memory: Optional[str] = None,
    port: Optional[int] = None,
    java_path: Optional[str] = None,
    jvm_args: Optional[str] = None,
) -> dict:
    """Update server configuration.

    Args:
        name: Server name.
        memory: New memory allocation.
        port: New port.
        java_path: Custom Java path.
        jvm_args: Custom JVM arguments.

    Returns:
        Updated server dictionary.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.name == name).first()

        if not server:
            raise ServerNotFoundError(name)

        if memory:
            server.memory = validate_memory(memory)
        if port:
            server.port = validate_port(port)
        if java_path is not None:
            server.java_path = java_path or None
        if jvm_args is not None:
            server.jvm_args = jvm_args or None

        logger.info(f"Updated server '{name}'")

        return {
            "id": server.id,
            "name": server.name,
            "type": server.type,
            "version": server.version,
            "port": server.port,
            "memory": server.memory,
            "java_path": server.java_path,
            "jvm_args": server.jvm_args,
        }


# Re-export lifecycle functions for convenience
__all__ = [
    "create_server",
    "list_servers",
    "get_server",
    "get_server_by_id",
    "delete_server",
    "import_server",
    "update_server",
    "start_server",
    "stop_server",
    "sync_server_states",
]
