"""Background task management for MSM - handles periodic tasks and cleanup."""
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import psutil

from .db import get_session, Server
from .console import get_console_manager

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for MSM."""

    _instance: Optional["BackgroundTaskManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "BackgroundTaskManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._running = False
        self._tasks: Dict[str, dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._initialized = True

    def register_task(
        self,
        name: str,
        callback: Callable[[], None],
        interval_seconds: float,
        run_immediately: bool = False,
    ) -> None:
        """Register a periodic background task.

        Args:
            name: Unique name for the task.
            callback: Function to call periodically.
            interval_seconds: How often to run the task.
            run_immediately: If True, run once immediately on registration.
        """
        self._tasks[name] = {
            "callback": callback,
            "interval": interval_seconds,
            "last_run": 0 if run_immediately else time.time(),
        }
        logger.info(f"Registered background task: {name} (interval: {interval_seconds}s)")

    def start(self) -> None:
        """Start the background task runner."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="msm-background-tasks",
        )
        self._thread.start()
        logger.info("Background task manager started")

    def stop(self) -> None:
        """Stop the background task runner."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Background task manager stopped")

    def _run_loop(self) -> None:
        """Main loop for running background tasks."""
        while self._running:
            now = time.time()

            for name, task in self._tasks.items():
                if now - task["last_run"] >= task["interval"]:
                    try:
                        task["callback"]()
                        task["last_run"] = now
                    except Exception as e:
                        logger.error(f"Background task '{name}' failed: {e}")

            # Sleep for a short interval to avoid busy-waiting
            time.sleep(1.0)


def get_background_manager() -> BackgroundTaskManager:
    """Get the singleton background task manager."""
    return BackgroundTaskManager()


# ============================================================================
# Built-in Background Tasks
# ============================================================================

def sync_server_states_task() -> None:
    """Periodic task to sync server states with actual process status.

    This catches any edge cases where process monitoring might have missed
    a server termination.
    """
    corrected = 0

    with get_session() as session:
        servers = session.query(Server).filter(Server.is_running.is_(True)).all()

        for server in servers:
            if server.pid:
                try:
                    # Check if process exists and is a Java process
                    if not psutil.pid_exists(server.pid):
                        logger.warning(
                            f"Server '{server.name}' (PID {server.pid}) not found, "
                            "marking as stopped"
                        )
                        server.is_running = False
                        server.pid = None
                        server.last_stopped = datetime.utcnow()
                        corrected += 1
                    else:
                        # Verify it's still a Java process
                        try:
                            proc = psutil.Process(server.pid)
                            proc_name = proc.name().lower()
                            if "java" not in proc_name:
                                logger.warning(
                                    f"Server '{server.name}' PID {server.pid} is not Java "
                                    f"(found: {proc_name}), marking as stopped"
                                )
                                server.is_running = False
                                server.pid = None
                                server.last_stopped = datetime.utcnow()
                                corrected += 1
                        except psutil.NoSuchProcess:
                            server.is_running = False
                            server.pid = None
                            server.last_stopped = datetime.utcnow()
                            corrected += 1
                except Exception as e:
                    logger.error(f"Error checking server '{server.name}': {e}")
            else:
                # is_running=True but no PID - invalid state
                logger.warning(
                    f"Server '{server.name}' marked as running but has no PID, "
                    "marking as stopped"
                )
                server.is_running = False
                corrected += 1

    if corrected > 0:
        logger.info(f"State sync corrected {corrected} server(s)")


def cleanup_dead_consoles_task() -> None:
    """Clean up console manager entries for dead processes."""
    console_manager = get_console_manager()
    cleaned = console_manager.cleanup_dead_processes()
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} dead console process(es)")


def check_port_conflicts_task() -> None:
    """Check for servers with port conflicts and log warnings."""
    from collections import defaultdict

    with get_session() as session:
        servers = session.query(Server).all()

        # Group servers by port
        port_servers: Dict[int, List[str]] = defaultdict(list)
        for server in servers:
            port_servers[server.port].append(server.name)

        # Log warnings for conflicting ports
        for port, names in port_servers.items():
            if len(names) > 1:
                logger.warning(
                    f"Port conflict detected: {len(names)} servers using port {port}: "
                    f"{', '.join(names)}"
                )


def initialize_background_tasks() -> None:
    """Initialize and start all background tasks."""
    manager = get_background_manager()

    # Sync server states every 10 seconds
    manager.register_task(
        "sync_server_states",
        sync_server_states_task,
        interval_seconds=10.0,
        run_immediately=True,
    )

    # Clean up dead consoles every 30 seconds
    manager.register_task(
        "cleanup_dead_consoles",
        cleanup_dead_consoles_task,
        interval_seconds=30.0,
    )

    # Check for port conflicts every 60 seconds
    manager.register_task(
        "check_port_conflicts",
        check_port_conflicts_task,
        interval_seconds=60.0,
        run_immediately=True,
    )

    manager.start()


def shutdown_background_tasks() -> None:
    """Stop all background tasks."""
    manager = get_background_manager()
    manager.stop()
