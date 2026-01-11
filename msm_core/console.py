"""Console management for MSM - handles process I/O streaming."""
import logging
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Maximum lines to keep in history per server
MAX_HISTORY_LINES = 1000


class ConsoleBuffer:
    """Thread-safe buffer for console output with history."""

    def __init__(self, server_id: int, max_lines: int = MAX_HISTORY_LINES):
        self.server_id = server_id
        self.max_lines = max_lines
        self._history: Deque[dict] = deque(maxlen=max_lines)
        self._lock = threading.Lock()
        self._subscribers: Set[Callable] = set()

    def add_line(self, line: str, stream: str = "stdout") -> dict:
        """Add a line to the buffer and notify subscribers.

        Args:
            line: The console output line.
            stream: Either 'stdout' or 'stderr'.

        Returns:
            The created line entry.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stream": stream,
            "line": line.rstrip(),
        }

        with self._lock:
            self._history.append(entry)

        # Notify subscribers (async callbacks)
        for callback in list(self._subscribers):
            try:
                callback(entry)
            except Exception as e:
                logger.warning(f"Console callback error: {e}")

        return entry

    def get_history(self, limit: Optional[int] = None) -> List[dict]:
        """Get console history.

        Args:
            limit: Max number of lines to return (newest first).

        Returns:
            List of line entries.
        """
        with self._lock:
            if limit:
                return list(self._history)[-limit:]
            return list(self._history)

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to new console output."""
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from console output."""
        self._subscribers.discard(callback)

    def clear(self) -> None:
        """Clear the history buffer."""
        with self._lock:
            self._history.clear()


class ServerProcess:
    """Wrapper for a running server process with I/O handling."""

    def __init__(
        self,
        server_id: int,
        process: subprocess.Popen,
        cwd: Path,
        on_exit: Optional[Callable[[int, int], None]] = None,
    ):
        self.server_id = server_id
        self.process = process
        self.cwd = cwd
        self.buffer = ConsoleBuffer(server_id)
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_exit = on_exit  # Callback: (server_id, exit_code) -> None
        self._exit_handled = False
        self._exit_lock = threading.Lock()

    def start_io_threads(self) -> None:
        """Start threads to read stdout, stderr, and monitor process."""
        self._running = True

        if self.process.stdout:
            self._stdout_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stdout, "stdout"),
                daemon=True,
                name=f"server-{self.server_id}-stdout",
            )
            self._stdout_thread.start()

        if self.process.stderr:
            self._stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stderr, "stderr"),
                daemon=True,
                name=f"server-{self.server_id}-stderr",
            )
            self._stderr_thread.start()

        # Start process monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_process,
            daemon=True,
            name=f"server-{self.server_id}-monitor",
        )
        self._monitor_thread.start()

    def _read_stream(self, stream, stream_name: str) -> None:
        """Read from a stream and add lines to buffer."""
        try:
            for line in iter(stream.readline, ""):
                if not self._running:
                    break
                if line:
                    self.buffer.add_line(line, stream_name)
        except Exception as e:
            logger.error(f"Error reading {stream_name} for server {self.server_id}: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _monitor_process(self) -> None:
        """Monitor the process and call exit callback when it terminates."""
        while self._running:
            exit_code = self.process.poll()
            if exit_code is not None:
                # Process has terminated
                self._handle_exit(exit_code)
                break
            time.sleep(0.5)  # Check every 500ms

    def _handle_exit(self, exit_code: int) -> None:
        """Handle process exit - call callback exactly once."""
        with self._exit_lock:
            if self._exit_handled:
                return
            self._exit_handled = True

        logger.info(f"Server {self.server_id} process exited with code {exit_code}")

        # Add exit message to console
        self.buffer.add_line(
            f"[MSM] Server process exited with code {exit_code}",
            "system"
        )

        # Call exit callback
        if self._on_exit:
            try:
                self._on_exit(self.server_id, exit_code)
            except Exception as e:
                logger.error(f"Error in exit callback for server {self.server_id}: {e}")

    def send_command(self, command: str) -> bool:
        """Send a command to the server stdin.

        Args:
            command: Command to send (newline will be added).

        Returns:
            True if command was sent successfully.
        """
        if not self.process.stdin:
            logger.warning(f"Server {self.server_id} has no stdin")
            return False

        if self.process.poll() is not None:
            logger.warning(f"Server {self.server_id} process has terminated")
            return False

        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            logger.debug(f"Sent command to server {self.server_id}: {command}")
            return True
        except Exception as e:
            logger.error(f"Error sending command to server {self.server_id}: {e}")
            return False

    def stop(self) -> None:
        """Stop reading threads."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if process is still running."""
        return self.process.poll() is None


class ConsoleManager:
    """Singleton manager for all server console sessions."""

    _instance: Optional["ConsoleManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ConsoleManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._processes: Dict[int, ServerProcess] = {}
        self._exit_callbacks: List[Callable[[int, int], None]] = []
        self._initialized = True

    def register_exit_callback(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback to be called when any server process exits.

        Args:
            callback: Function taking (server_id, exit_code).
        """
        self._exit_callbacks.append(callback)

    def _on_process_exit(self, server_id: int, exit_code: int) -> None:
        """Internal handler for process exit."""
        # Call all registered exit callbacks
        for callback in self._exit_callbacks:
            try:
                callback(server_id, exit_code)
            except Exception as e:
                logger.error(f"Error in exit callback: {e}")

    def register_process(
        self,
        server_id: int,
        process: subprocess.Popen,
        cwd: Path,
    ) -> ServerProcess:
        """Register a new server process for console management.

        Args:
            server_id: The server database ID.
            process: The subprocess.Popen object.
            cwd: Working directory of the server.

        Returns:
            The ServerProcess wrapper.
        """
        if server_id in self._processes:
            # Clean up old process if exists
            old = self._processes[server_id]
            old.stop()

        server_proc = ServerProcess(
            server_id,
            process,
            cwd,
            on_exit=self._on_process_exit,
        )
        server_proc.start_io_threads()
        self._processes[server_id] = server_proc

        logger.info(f"Registered console for server {server_id}")
        return server_proc

    def unregister_process(self, server_id: int) -> None:
        """Unregister a server process.

        Args:
            server_id: The server database ID.
        """
        if server_id in self._processes:
            self._processes[server_id].stop()
            del self._processes[server_id]
            logger.info(f"Unregistered console for server {server_id}")

    def get_process(self, server_id: int) -> Optional[ServerProcess]:
        """Get a server process by ID.

        Args:
            server_id: The server database ID.

        Returns:
            The ServerProcess or None if not found.
        """
        return self._processes.get(server_id)

    def send_command(self, server_id: int, command: str) -> bool:
        """Send a command to a server.

        Args:
            server_id: The server database ID.
            command: The command to send.

        Returns:
            True if the command was sent successfully.
        """
        proc = self._processes.get(server_id)
        if not proc:
            logger.warning(f"No console registered for server {server_id}")
            return False
        return proc.send_command(command)

    def get_history(self, server_id: int, limit: Optional[int] = None) -> List[dict]:
        """Get console history for a server.

        Args:
            server_id: The server database ID.
            limit: Max number of lines to return.

        Returns:
            List of console line entries.
        """
        proc = self._processes.get(server_id)
        if not proc:
            return []
        return proc.buffer.get_history(limit)

    def subscribe(self, server_id: int, callback: Callable) -> bool:
        """Subscribe to console output for a server.

        Args:
            server_id: The server database ID.
            callback: Function to call with each new line.

        Returns:
            True if subscription was successful.
        """
        proc = self._processes.get(server_id)
        if not proc:
            return False
        proc.buffer.subscribe(callback)
        return True

    def unsubscribe(self, server_id: int, callback: Callable) -> bool:
        """Unsubscribe from console output.

        Args:
            server_id: The server database ID.
            callback: The callback function to remove.

        Returns:
            True if unsubscription was successful.
        """
        proc = self._processes.get(server_id)
        if not proc:
            return False
        proc.buffer.unsubscribe(callback)
        return True

    def cleanup_dead_processes(self) -> int:
        """Remove processes that are no longer running.

        Returns:
            Number of processes cleaned up.
        """
        dead = []
        for server_id, proc in self._processes.items():
            if not proc.is_running:
                dead.append(server_id)

        for server_id in dead:
            self.unregister_process(server_id)

        return len(dead)


def get_console_manager() -> ConsoleManager:
    """Get the singleton console manager instance."""
    return ConsoleManager()
