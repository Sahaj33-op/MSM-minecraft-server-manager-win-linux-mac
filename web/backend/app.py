"""MSM Web Backend - FastAPI Application."""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from msm_core import api
from msm_core.lifecycle import (
    start_server,
    stop_server,
    restart_server,
    sync_server_states,
    get_server_status,
    send_command,
    get_console_history,
)
from msm_core.monitor import get_system_stats, get_process_stats
from msm_core.exceptions import (
    MSMError,
    ServerNotFoundError,
    ServerAlreadyRunningError,
    ServerNotRunningError,
    ValidationError,
)
from .ws_console import handle_console_websocket

logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("MSM API starting up...")
    corrected = sync_server_states()
    if corrected > 0:
        logger.info(f"Corrected state for {corrected} server(s)")

    yield

    # Shutdown
    logger.info("MSM API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MSM API",
    description="Minecraft Server Manager REST API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5000", "http://127.0.0.1:5173", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateServerRequest(BaseModel):
    name: str
    type: str = "paper"
    version: str = "1.20.4"
    memory: str = "2G"
    port: int = 25565


class UpdateServerRequest(BaseModel):
    memory: Optional[str] = None
    port: Optional[int] = None
    java_path: Optional[str] = None
    jvm_args: Optional[str] = None


class ImportServerRequest(BaseModel):
    name: str
    path: str
    type: str = "paper"
    version: str = "1.20.4"
    memory: str = "2G"
    port: int = 25565


class ServerResponse(BaseModel):
    id: int
    name: str
    type: str
    version: str
    path: str
    port: int
    memory: str
    is_running: bool
    pid: Optional[int] = None
    created_at: Optional[str] = None


class StatusResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


# ============================================================================
# Exception Handlers
# ============================================================================

def handle_msm_error(e: MSMError) -> HTTPException:
    """Convert MSM exceptions to HTTP exceptions."""
    if isinstance(e, ServerNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, (ServerAlreadyRunningError, ServerNotRunningError, ValidationError)):
        return HTTPException(status_code=400, detail=str(e))
    else:
        return HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Server Endpoints
# ============================================================================

@app.get("/api/v1/servers", response_model=list, tags=["Servers"])
def get_servers():
    """List all servers."""
    return api.list_servers()


@app.post("/api/v1/servers", tags=["Servers"])
def create_server(req: CreateServerRequest):
    """Create a new server."""
    try:
        server = api.create_server(
            name=req.name,
            server_type=req.type,
            version=req.version,
            memory=req.memory,
            port=req.port,
        )
        return {
            "id": server.id,
            "name": server.name,
            "type": server.type,
            "version": server.version,
            "port": server.port,
            "memory": server.memory,
            "message": f"Server '{server.name}' created successfully",
        }
    except MSMError as e:
        raise handle_msm_error(e)
    except Exception as e:
        logger.exception("Failed to create server")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/servers/{server_id}", tags=["Servers"])
def get_server_by_id(server_id: int):
    """Get server by ID."""
    server = api.get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")
    return server


@app.get("/api/v1/servers/name/{name}", tags=["Servers"])
def get_server_by_name(name: str):
    """Get server by name."""
    server = api.get_server(name)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
    return server


@app.patch("/api/v1/servers/{server_id}", tags=["Servers"])
def update_server(server_id: int, req: UpdateServerRequest):
    """Update server configuration."""
    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        updated = api.update_server(
            name=server["name"],
            memory=req.memory,
            port=req.port,
            java_path=req.java_path,
            jvm_args=req.jvm_args,
        )
        return updated
    except MSMError as e:
        raise handle_msm_error(e)


@app.delete("/api/v1/servers/{server_id}", tags=["Servers"])
def delete_server(server_id: int, keep_files: bool = False):
    """Delete a server."""
    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        api.delete_server(server["name"], keep_files=keep_files)
        return {"status": "deleted", "name": server["name"]}
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/servers/import", tags=["Servers"])
def import_server(req: ImportServerRequest):
    """Import an existing server directory."""
    try:
        from pathlib import Path
        server = api.import_server(
            name=req.name,
            server_type=req.type,
            version=req.version,
            path=Path(req.path),
            memory=req.memory,
            port=req.port,
        )
        return {
            "id": server.id,
            "name": server.name,
            "message": f"Server '{server.name}' imported successfully",
        }
    except MSMError as e:
        raise handle_msm_error(e)


# ============================================================================
# Server Control Endpoints
# ============================================================================

@app.post("/api/v1/servers/{server_id}/start", response_model=StatusResponse, tags=["Control"])
def start_server_endpoint(server_id: int):
    """Start a server."""
    try:
        start_server(server_id)
        return {"status": "started"}
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/servers/{server_id}/stop", response_model=StatusResponse, tags=["Control"])
def stop_server_endpoint(server_id: int):
    """Stop a server."""
    try:
        stop_server(server_id)
        return {"status": "stopped"}
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/servers/{server_id}/restart", response_model=StatusResponse, tags=["Control"])
def restart_server_endpoint(server_id: int):
    """Restart a server."""
    try:
        restart_server(server_id)
        return {"status": "restarted"}
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/servers/{server_id}/status", tags=["Control"])
def get_status(server_id: int):
    """Get detailed server status including process info."""
    try:
        return get_server_status(server_id)
    except MSMError as e:
        raise handle_msm_error(e)


# ============================================================================
# Monitoring Endpoints
# ============================================================================

@app.get("/api/v1/stats", tags=["Monitoring"])
def get_stats():
    """Get system statistics."""
    return get_system_stats()


@app.get("/api/v1/servers/{server_id}/stats", tags=["Monitoring"])
def get_server_stats(server_id: int):
    """Get server process statistics."""
    server = api.get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

    if not server["is_running"] or not server["pid"]:
        raise HTTPException(status_code=400, detail="Server is not running")

    stats = get_process_stats(server["pid"])
    if not stats:
        raise HTTPException(status_code=400, detail="Could not get process stats")

    return stats


# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/", tags=["System"])
def root():
    """Root endpoint."""
    return {
        "name": "MSM API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ============================================================================
# Console Endpoints
# ============================================================================

class CommandRequest(BaseModel):
    command: str


@app.post("/api/v1/servers/{server_id}/console/command", tags=["Console"])
def send_console_command(server_id: int, req: CommandRequest):
    """Send a command to the server console."""
    try:
        success = send_command(server_id, req.command)
        return {"success": success, "command": req.command}
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/servers/{server_id}/console/history", tags=["Console"])
def get_console_history_endpoint(server_id: int, limit: int = 100):
    """Get console history for a server."""
    try:
        history = get_console_history(server_id, limit=limit)
        return {"lines": history}
    except MSMError as e:
        raise handle_msm_error(e)


# ============================================================================
# WebSocket Console
# ============================================================================

@app.websocket("/api/v1/servers/{server_id}/console/ws")
async def console_websocket(websocket: WebSocket, server_id: int):
    """WebSocket endpoint for real-time console streaming.

    Connect to this endpoint to receive live console output
    and send commands to a running server.

    Message types from server:
    - {"type": "history", "lines": [...]} - Initial history
    - {"type": "output", "data": {...}} - Console output line
    - {"type": "command_ack", "success": bool, "command": str} - Command acknowledgment
    - {"type": "error", "message": str} - Error message
    - {"type": "heartbeat"} - Keep-alive ping

    Message types to server:
    - {"type": "command", "command": str} - Send a command
    - {"type": "ping"} - Ping for pong response
    """
    await handle_console_websocket(websocket, server_id)
