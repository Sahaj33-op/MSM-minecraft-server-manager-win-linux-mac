"""WebSocket console handler for MSM Web Backend."""
import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

from msm_core.console import get_console_manager
from msm_core.lifecycle import send_command, get_console_history
from msm_core.exceptions import ServerNotFoundError, ServerNotRunningError

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections for server consoles."""

    def __init__(self):
        # server_id -> set of websocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> asyncio queue for sending messages
        self._queues: Dict[WebSocket, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, server_id: int) -> bool:
        """Accept a WebSocket connection for a server console.

        Args:
            websocket: The WebSocket connection.
            server_id: The server ID to connect to.

        Returns:
            True if connection was successful.
        """
        await websocket.accept()

        # Initialize connection set for this server if needed
        if server_id not in self._connections:
            self._connections[server_id] = set()

        self._connections[server_id].add(websocket)

        # Create message queue for this connection
        self._queues[websocket] = asyncio.Queue()

        # Subscribe to console output
        console_manager = get_console_manager()
        server_proc = console_manager.get_process(server_id)

        if server_proc:
            # Create a callback that queues messages for this websocket
            def on_console_output(entry: dict):
                try:
                    # Use thread-safe queue put
                    asyncio.get_event_loop().call_soon_threadsafe(
                        self._queues[websocket].put_nowait, entry
                    )
                except Exception:
                    pass

            server_proc.buffer.subscribe(on_console_output)

            # Store the callback for cleanup
            websocket.state.console_callback = on_console_output
            websocket.state.server_id = server_id

        logger.info(f"WebSocket connected for server {server_id}")
        return True

    async def disconnect(self, websocket: WebSocket, server_id: int) -> None:
        """Disconnect a WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            server_id: The server ID.
        """
        # Unsubscribe from console output
        if hasattr(websocket.state, "console_callback"):
            console_manager = get_console_manager()
            server_proc = console_manager.get_process(server_id)
            if server_proc:
                server_proc.buffer.unsubscribe(websocket.state.console_callback)

        # Remove from connections
        if server_id in self._connections:
            self._connections[server_id].discard(websocket)
            if not self._connections[server_id]:
                del self._connections[server_id]

        # Remove queue
        if websocket in self._queues:
            del self._queues[websocket]

        logger.info(f"WebSocket disconnected for server {server_id}")

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a specific WebSocket.

        Args:
            websocket: The WebSocket connection.
            message: The message to send.
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")

    async def broadcast(self, server_id: int, message: dict) -> None:
        """Broadcast a message to all connections for a server.

        Args:
            server_id: The server ID.
            message: The message to send.
        """
        if server_id not in self._connections:
            return

        dead_connections = []
        for websocket in self._connections[server_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.append(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            await self.disconnect(websocket, server_id)

    def get_queue(self, websocket: WebSocket) -> asyncio.Queue:
        """Get the message queue for a WebSocket.

        Args:
            websocket: The WebSocket connection.

        Returns:
            The asyncio Queue for this connection.
        """
        return self._queues.get(websocket)


# Singleton instance
connection_manager = WebSocketConnectionManager()


async def handle_console_websocket(websocket: WebSocket, server_id: int) -> None:
    """Handle a WebSocket connection for a server console.

    This function runs the main WebSocket loop, receiving commands
    from the client and sending console output.

    Args:
        websocket: The WebSocket connection.
        server_id: The server ID.
    """
    await connection_manager.connect(websocket, server_id)

    try:
        # Send initial console history
        try:
            history = get_console_history(server_id, limit=100)
            await connection_manager.send_personal(websocket, {
                "type": "history",
                "lines": history,
            })
        except (ServerNotFoundError, ServerNotRunningError):
            await connection_manager.send_personal(websocket, {
                "type": "error",
                "message": "Server is not running",
            })

        # Start tasks for sending and receiving
        send_task = asyncio.create_task(_send_loop(websocket, server_id))
        receive_task = asyncio.create_task(_receive_loop(websocket, server_id))

        # Wait for either task to complete (or fail)
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for server {server_id}")
    except Exception as e:
        logger.error(f"WebSocket error for server {server_id}: {e}")
    finally:
        await connection_manager.disconnect(websocket, server_id)


async def _send_loop(websocket: WebSocket, server_id: int) -> None:
    """Send console output to the WebSocket.

    Args:
        websocket: The WebSocket connection.
        server_id: The server ID.
    """
    queue = connection_manager.get_queue(websocket)
    if not queue:
        return

    while True:
        try:
            # Wait for new console output
            entry = await asyncio.wait_for(queue.get(), timeout=30.0)
            await connection_manager.send_personal(websocket, {
                "type": "output",
                "data": entry,
            })
        except asyncio.TimeoutError:
            # Send heartbeat to keep connection alive
            try:
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break
        except Exception as e:
            logger.warning(f"Send loop error: {e}")
            break


async def _receive_loop(websocket: WebSocket, server_id: int) -> None:
    """Receive commands from the WebSocket.

    Args:
        websocket: The WebSocket connection.
        server_id: The server ID.
    """
    while True:
        try:
            data = await websocket.receive_json()

            if data.get("type") == "command":
                command = data.get("command", "")
                if command:
                    try:
                        success = send_command(server_id, command)
                        await connection_manager.send_personal(websocket, {
                            "type": "command_ack",
                            "success": success,
                            "command": command,
                        })
                    except ServerNotRunningError:
                        await connection_manager.send_personal(websocket, {
                            "type": "error",
                            "message": "Server is not running",
                        })

            elif data.get("type") == "ping":
                await connection_manager.send_personal(websocket, {
                    "type": "pong",
                })

        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.warning(f"Receive loop error: {e}")
            break
