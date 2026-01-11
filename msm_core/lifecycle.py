"""Server lifecycle management for MSM."""
import logging
import os
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import psutil

from .db import get_session, Server
from .console import get_console_manager
from .exceptions import (
    ServerNotFoundError,
    ServerAlreadyRunningError,
    ServerNotRunningError,
    JavaNotFoundError,
    PortInUseError,
)
from platform_adapters import get_adapter

logger = logging.getLogger(__name__)

# How long to wait for graceful shutdown before force killing
GRACEFUL_SHUTDOWN_TIMEOUT = 30


def check_port_available(port: int) -> Tuple[bool, Optional[int]]:
    """Check if a port is available for use.

    Args:
        port: The port number to check.

    Returns:
        Tuple of (is_available, pid_using_port).
    """
    # First try to bind to the port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            return True, None
    except OSError:
        pass

    # Port is in use, try to find the PID
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == "LISTEN":
            return False, conn.pid

    return False, None


def start_server(server_id: int) -> bool:
    """Start a Minecraft server.

    Args:
        server_id: The database ID of the server to start.

    Returns:
        True if the server was started successfully.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
        ServerAlreadyRunningError: If the server is already running.
        JavaNotFoundError: If Java is not found on the system.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()

        if not server:
            raise ServerNotFoundError(server_id)

        if server.is_running:
            logger.info(f"Server '{server.name}' is already running (PID: {server.pid})")
            raise ServerAlreadyRunningError(server.name)

        # Check if port is available before trying to start
        port_available, blocking_pid = check_port_available(server.port)
        if not port_available:
            logger.error(f"Port {server.port} is already in use by PID {blocking_pid}")
            raise PortInUseError(server.port, blocking_pid)

        adapter = get_adapter()

        # Get Java path
        java_path = server.java_path or adapter.get_java_path()
        if not java_path:
            logger.error("Java not found on system")
            raise JavaNotFoundError()

        # Construct command
        memory_flag = f"-Xmx{server.memory}"
        jvm_args = server.jvm_args.split() if server.jvm_args else []
        cmd = [java_path, memory_flag, *jvm_args, "-jar", "server.jar", "nogui"]

        cwd = Path(server.path)

        # Ensure EULA is accepted
        eula_path = cwd / "eula.txt"
        if not eula_path.exists():
            logger.info(f"Creating eula.txt for server '{server.name}'")
            with open(eula_path, "w") as f:
                f.write("eula=true\n")

        # Merge with system environment
        env = {**os.environ}

        try:
            logger.info(f"Starting server '{server.name}' with command: {' '.join(cmd)}")
            proc = adapter.start_process(cmd, cwd, env)

            # Register with console manager for I/O handling
            console_manager = get_console_manager()
            console_manager.register_process(server.id, proc, cwd)

            server.is_running = True
            server.pid = proc.pid
            server.last_started = datetime.utcnow()

            logger.info(f"Server '{server.name}' started with PID {proc.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start server '{server.name}': {e}")
            raise


def stop_server(server_id: int, force: bool = False) -> bool:
    """Stop a Minecraft server.

    Args:
        server_id: The database ID of the server to stop.
        force: If True, forcefully kill the process without graceful shutdown.

    Returns:
        True if the server was stopped successfully.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
        ServerNotRunningError: If the server is not running.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()

        if not server:
            raise ServerNotFoundError(server_id)

        if not server.is_running or not server.pid:
            raise ServerNotRunningError(server.name)

        console_manager = get_console_manager()
        adapter = get_adapter()

        try:
            logger.info(f"Stopping server '{server.name}' (PID: {server.pid})")

            # Try graceful shutdown first (send "stop" command)
            if not force:
                server_proc = console_manager.get_process(server_id)
                if server_proc and server_proc.send_command("stop"):
                    logger.info(f"Sent 'stop' command to server '{server.name}'")

                    # Wait for graceful shutdown
                    start_time = time.time()
                    while time.time() - start_time < GRACEFUL_SHUTDOWN_TIMEOUT:
                        if not psutil.pid_exists(server.pid):
                            break
                        time.sleep(0.5)

                    if not psutil.pid_exists(server.pid):
                        logger.info(f"Server '{server.name}' stopped gracefully")
                        console_manager.unregister_process(server_id)
                        server.is_running = False
                        server.pid = None
                        server.last_stopped = datetime.utcnow()
                        return True

                    logger.warning(
                        f"Server '{server.name}' did not stop gracefully after "
                        f"{GRACEFUL_SHUTDOWN_TIMEOUT}s, forcing..."
                    )

            # Force stop
            if adapter.stop_process(server.pid):
                console_manager.unregister_process(server_id)
                server.is_running = False
                server.pid = None
                server.last_stopped = datetime.utcnow()
                logger.info(f"Server '{server.name}' stopped")
                return True
            else:
                logger.warning(f"Failed to stop server '{server.name}'")
                return False

        except Exception as e:
            logger.error(f"Error stopping server '{server.name}': {e}")
            raise


def restart_server(server_id: int) -> bool:
    """Restart a Minecraft server.

    Args:
        server_id: The database ID of the server to restart.

    Returns:
        True if the server was restarted successfully.
    """
    try:
        stop_server(server_id)
    except ServerNotRunningError:
        pass  # Server wasn't running, that's fine

    return start_server(server_id)


def get_server_status(server_id: int) -> dict:
    """Get the current status of a server.

    This function queries the OS process table to verify the actual running state,
    treating the OS as the source of truth rather than relying solely on the database.

    Args:
        server_id: The database ID of the server.

    Returns:
        Dictionary with server status information.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()

        if not server:
            raise ServerNotFoundError(server_id)

        # IMPORTANT: Verify actual running state against OS process table
        # The OS is the source of truth, not the database
        actual_running = False
        if server.pid:
            try:
                proc = psutil.Process(server.pid)
                # Verify it's actually a Java process (our server)
                if "java" in proc.name().lower() and proc.is_running():
                    actual_running = True
            except psutil.NoSuchProcess:
                pass

        # Correct database state if it differs from reality
        if server.is_running != actual_running:
            logger.info(
                f"State mismatch for server '{server.name}': "
                f"DB says {'running' if server.is_running else 'stopped'}, "
                f"OS says {'running' if actual_running else 'stopped'}. Correcting."
            )
            server.is_running = actual_running
            if not actual_running:
                server.pid = None
                server.last_stopped = datetime.utcnow()

        status = {
            "id": server.id,
            "name": server.name,
            "type": server.type,
            "version": server.version,
            "port": server.port,
            "is_running": actual_running,
            "pid": server.pid if actual_running else None,
            "memory": server.memory,
            "last_started": server.last_started.isoformat() if server.last_started else None,
            "last_stopped": server.last_stopped.isoformat() if server.last_stopped else None,
        }

        # Get process stats if running
        if actual_running and server.pid:
            try:
                proc = psutil.Process(server.pid)
                with proc.oneshot():
                    status["process"] = {
                        "cpu_percent": proc.cpu_percent(),
                        "memory_rss": proc.memory_info().rss,
                        "status": proc.status(),
                        "uptime": (datetime.utcnow() - datetime.fromtimestamp(proc.create_time())).total_seconds(),
                    }
            except psutil.NoSuchProcess:
                # Process died between our check and getting stats
                pass

        return status


def sync_server_states() -> int:
    """Reconcile database state with actual running processes.

    This should be called on startup to fix any stale state from
    crashes or unexpected shutdowns.

    Returns:
        Number of servers whose state was corrected.
    """
    corrected = 0

    with get_session() as session:
        servers = session.query(Server).filter(Server.is_running.is_(True)).all()

        for server in servers:
            if server.pid:
                if not psutil.pid_exists(server.pid):
                    logger.warning(
                        f"Server '{server.name}' marked as running but PID {server.pid} doesn't exist. "
                        "Correcting state."
                    )
                    server.is_running = False
                    server.pid = None
                    corrected += 1
                else:
                    # Verify it's actually our Java process
                    try:
                        proc = psutil.Process(server.pid)
                        if "java" not in proc.name().lower():
                            logger.warning(
                                f"Server '{server.name}' PID {server.pid} is not a Java process. "
                                "Correcting state."
                            )
                            server.is_running = False
                            server.pid = None
                            corrected += 1
                    except psutil.NoSuchProcess:
                        server.is_running = False
                        server.pid = None
                        corrected += 1
            else:
                # is_running=True but no PID, invalid state
                logger.warning(f"Server '{server.name}' marked as running but has no PID. Correcting state.")
                server.is_running = False
                corrected += 1

    if corrected > 0:
        logger.info(f"Corrected state for {corrected} server(s)")

    return corrected


def send_command(server_id: int, command: str) -> bool:
    """Send a command to a running server's console.

    Args:
        server_id: The database ID of the server.
        command: The command to send.

    Returns:
        True if the command was sent successfully.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
        ServerNotRunningError: If the server is not running.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()

        if not server:
            raise ServerNotFoundError(server_id)

        if not server.is_running:
            raise ServerNotRunningError(server.name)

    console_manager = get_console_manager()
    return console_manager.send_command(server_id, command)


def get_console_history(server_id: int, limit: int = 100) -> list:
    """Get console history for a server.

    Args:
        server_id: The database ID of the server.
        limit: Maximum number of lines to return.

    Returns:
        List of console line entries.

    Raises:
        ServerNotFoundError: If the server doesn't exist.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()

        if not server:
            raise ServerNotFoundError(server_id)

    console_manager = get_console_manager()
    return console_manager.get_history(server_id, limit)


def _on_server_process_exit(server_id: int, exit_code: int) -> None:
    """Callback invoked when a server process terminates.

    This updates the database to reflect that the server is no longer running.

    Args:
        server_id: The server database ID.
        exit_code: The process exit code.
    """
    logger.info(f"Server {server_id} process exited with code {exit_code}, updating database")

    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if server:
            server.is_running = False
            server.pid = None
            server.last_stopped = datetime.utcnow()
            logger.info(f"Server '{server.name}' marked as stopped in database")

    # Clean up the process from console manager
    console_manager = get_console_manager()
    console_manager.unregister_process(server_id)


def initialize_process_monitoring() -> None:
    """Initialize process monitoring by registering the exit callback.

    This should be called once at application startup.
    """
    console_manager = get_console_manager()
    console_manager.register_exit_callback(_on_server_process_exit)
    logger.info("Process monitoring initialized")
