"""MSM Web Backend - FastAPI Application."""
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
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
    initialize_process_monitoring,
)
from msm_core.background import (
    initialize_background_tasks,
    shutdown_background_tasks,
)
from msm_core.monitor import get_system_stats, get_process_stats
from msm_core.exceptions import (
    MSMError,
    ServerNotFoundError,
    ServerAlreadyRunningError,
    ServerNotRunningError,
    PortInUseError,
    ValidationError,
)
from .ws_console import handle_console_websocket

logger = logging.getLogger(__name__)

# Track startup time for health checks
_startup_time: Optional[datetime] = None


# ============================================================================
# Lifespan Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    global _startup_time

    # Startup
    logger.info("=" * 60)
    logger.info("MSM API starting up...")
    logger.info("=" * 60)

    _startup_time = datetime.utcnow()

    try:
        # Initialize process monitoring (detects when servers stop)
        initialize_process_monitoring()
        logger.info("✓ Process monitoring initialized")

        # Sync server states with running processes
        corrected = sync_server_states()
        if corrected > 0:
            logger.info(f"✓ Corrected state for {corrected} server(s)")
        else:
            logger.info("✓ Server states verified")

        # Start background tasks (periodic state sync, cleanup)
        initialize_background_tasks()
        logger.info("✓ Background tasks started")

        logger.info("=" * 60)
        logger.info("MSM API ready to serve requests")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to initialize MSM API: {e}")
        raise

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("MSM API shutting down...")
    logger.info("=" * 60)

    try:
        # Stop background tasks
        shutdown_background_tasks()
        logger.info("✓ Background tasks stopped")

        logger.info("MSM API shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


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
    elif isinstance(e, PortInUseError):
        return HTTPException(status_code=409, detail=str(e))
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
    """Comprehensive health check endpoint."""
    from msm_core.db import get_session, Server
    from msm_core.console import get_console_manager

    health = {
        "status": "healthy",
        "version": "0.1.0",
        "uptime_seconds": None,
        "servers": {
            "total": 0,
            "running": 0,
        },
        "checks": {
            "database": False,
            "console_manager": False,
        },
    }

    # Calculate uptime
    if _startup_time:
        health["uptime_seconds"] = (datetime.utcnow() - _startup_time).total_seconds()

    # Check database
    try:
        with get_session() as session:
            servers = session.query(Server).all()
            health["servers"]["total"] = len(servers)
            health["servers"]["running"] = sum(1 for s in servers if s.is_running)
            health["checks"]["database"] = True
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["database_error"] = str(e)

    # Check console manager
    try:
        console_manager = get_console_manager()
        health["checks"]["console_manager"] = True
        health["checks"]["active_consoles"] = len(console_manager._processes)
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["console_manager_error"] = str(e)

    return health


@app.get("/api/v1/info", tags=["System"])
def api_info():
    """API info endpoint."""
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


# ============================================================================
# Backup Endpoints
# ============================================================================

class CreateBackupRequest(BaseModel):
    stop_first: bool = False
    backup_type: str = "manual"


@app.get("/api/v1/backups", tags=["Backups"])
def list_all_backups():
    """List all backups."""
    from msm_core.backups import list_backups
    return list_backups()


@app.get("/api/v1/servers/{server_id}/backups", tags=["Backups"])
def list_server_backups(server_id: int):
    """List backups for a specific server."""
    from msm_core.backups import list_backups

    server = api.get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

    return list_backups(server_id)


@app.post("/api/v1/servers/{server_id}/backups", tags=["Backups"])
def create_backup(server_id: int, req: CreateBackupRequest = None):
    """Create a backup of a server."""
    from msm_core.backups import create_backup as do_create_backup

    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        req = req or CreateBackupRequest()
        result = do_create_backup(
            server_id=server_id,
            stop_first=req.stop_first,
            backup_type=req.backup_type,
        )
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/backups/{backup_id}", tags=["Backups"])
def get_backup(backup_id: int):
    """Get backup details."""
    from msm_core.backups import get_backup_by_id

    backup = get_backup_by_id(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")
    return backup


@app.post("/api/v1/backups/{backup_id}/restore", tags=["Backups"])
def restore_backup(backup_id: int):
    """Restore a server from backup."""
    from msm_core.backups import restore_backup as do_restore

    try:
        do_restore(backup_id)
        return {"status": "restored", "backup_id": backup_id}
    except MSMError as e:
        raise handle_msm_error(e)


@app.delete("/api/v1/backups/{backup_id}", tags=["Backups"])
def delete_backup(backup_id: int, delete_file: bool = True):
    """Delete a backup."""
    from msm_core.backups import delete_backup as do_delete

    try:
        do_delete(backup_id, delete_file=delete_file)
        return {"status": "deleted", "backup_id": backup_id}
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/backups/prune", tags=["Backups"])
def prune_backups(server_id: Optional[int] = None, keep_count: int = 5, keep_days: Optional[int] = None):
    """Prune old backups."""
    from msm_core.backups import prune_backups as do_prune

    deleted = do_prune(server_id, keep_count=keep_count, keep_days=keep_days)
    return {"deleted_count": deleted}


# ============================================================================
# Plugin Endpoints
# ============================================================================

class InstallPluginRequest(BaseModel):
    source: str  # modrinth, hangar, url
    project_id: Optional[str] = None
    url: Optional[str] = None
    version_id: Optional[str] = None


@app.get("/api/v1/plugins/search", tags=["Plugins"])
def search_plugins(query: str, source: str = "modrinth", mc_version: Optional[str] = None, limit: int = 10):
    """Search for plugins on Modrinth or Hangar."""
    from msm_core.plugins import search_modrinth, search_hangar

    try:
        if source == "modrinth":
            return search_modrinth(query, mc_version=mc_version, limit=limit)
        elif source == "hangar":
            return search_hangar(query, mc_version=mc_version, limit=limit)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/servers/{server_id}/plugins", tags=["Plugins"])
def list_server_plugins(server_id: int):
    """List installed plugins for a server."""
    from msm_core.plugins import list_plugins

    server = api.get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

    return list_plugins(server_id)


@app.post("/api/v1/servers/{server_id}/plugins", tags=["Plugins"])
def install_plugin(server_id: int, req: InstallPluginRequest):
    """Install a plugin on a server."""
    from msm_core.plugins import install_from_modrinth, install_from_url

    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        if req.source == "modrinth" and req.project_id:
            result = install_from_modrinth(
                server_id=server_id,
                project_id=req.project_id,
                version_id=req.version_id,
                mc_version=server["version"],
            )
        elif req.source == "url" and req.url:
            result = install_from_url(server_id=server_id, url=req.url)
        else:
            raise HTTPException(status_code=400, detail="Invalid installation request")

        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/plugins/{plugin_id}", tags=["Plugins"])
def get_plugin(plugin_id: int):
    """Get plugin details."""
    from msm_core.plugins import get_plugin_by_id

    plugin = get_plugin_by_id(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    return plugin


@app.delete("/api/v1/plugins/{plugin_id}", tags=["Plugins"])
def uninstall_plugin(plugin_id: int, delete_file: bool = True):
    """Uninstall a plugin."""
    from msm_core.plugins import uninstall_plugin as do_uninstall

    try:
        do_uninstall(plugin_id, delete_file=delete_file)
        return {"status": "uninstalled", "plugin_id": plugin_id}
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/plugins/{plugin_id}/enable", tags=["Plugins"])
def enable_plugin(plugin_id: int):
    """Enable a disabled plugin."""
    from msm_core.plugins import toggle_plugin

    try:
        result = toggle_plugin(plugin_id, enabled=True)
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/plugins/{plugin_id}/disable", tags=["Plugins"])
def disable_plugin(plugin_id: int):
    """Disable a plugin."""
    from msm_core.plugins import toggle_plugin

    try:
        result = toggle_plugin(plugin_id, enabled=False)
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/servers/{server_id}/plugins/updates", tags=["Plugins"])
def check_plugin_updates(server_id: int):
    """Check for plugin updates."""
    from msm_core.plugins import check_plugin_updates as do_check

    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        return do_check(server_id)
    except MSMError as e:
        raise handle_msm_error(e)


# ============================================================================
# Schedule Endpoints
# ============================================================================

class CreateScheduleRequest(BaseModel):
    action: str
    cron: str
    payload: Optional[str] = None
    enabled: bool = True


class UpdateScheduleRequest(BaseModel):
    cron: Optional[str] = None
    enabled: Optional[bool] = None
    payload: Optional[str] = None


@app.get("/api/v1/schedules", tags=["Schedules"])
def list_all_schedules():
    """List all schedules."""
    from msm_core.scheduler import list_schedules
    return list_schedules()


@app.get("/api/v1/servers/{server_id}/schedules", tags=["Schedules"])
def list_server_schedules(server_id: int):
    """List schedules for a specific server."""
    from msm_core.scheduler import list_schedules

    server = api.get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

    return list_schedules(server_id)


@app.post("/api/v1/servers/{server_id}/schedules", tags=["Schedules"])
def create_schedule(server_id: int, req: CreateScheduleRequest):
    """Create a new schedule."""
    from msm_core.scheduler import create_schedule as do_create

    try:
        server = api.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server with ID {server_id} not found")

        result = do_create(
            server_id=server_id,
            action=req.action,
            cron_expr=req.cron,
            payload=req.payload,
            enabled=req.enabled,
        )
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/schedules/{schedule_id}", tags=["Schedules"])
def get_schedule(schedule_id: int):
    """Get schedule details."""
    from msm_core.scheduler import get_schedule_by_id

    schedule = get_schedule_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return schedule


@app.patch("/api/v1/schedules/{schedule_id}", tags=["Schedules"])
def update_schedule(schedule_id: int, req: UpdateScheduleRequest):
    """Update a schedule."""
    from msm_core.scheduler import update_schedule as do_update

    try:
        result = do_update(
            schedule_id=schedule_id,
            cron_expr=req.cron,
            enabled=req.enabled,
            payload=req.payload,
        )
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.delete("/api/v1/schedules/{schedule_id}", tags=["Schedules"])
def delete_schedule(schedule_id: int):
    """Delete a schedule."""
    from msm_core.scheduler import delete_schedule as do_delete

    try:
        do_delete(schedule_id)
        return {"status": "deleted", "schedule_id": schedule_id}
    except MSMError as e:
        raise handle_msm_error(e)


# ============================================================================
# Java Endpoints
# ============================================================================

@app.get("/api/v1/java/installed", tags=["Java"])
def list_installed_java():
    """List installed Java runtimes."""
    from msm_core.java_manager import detect_installed_javas
    return detect_installed_javas()


@app.get("/api/v1/java/managed", tags=["Java"])
def list_managed_java():
    """List MSM-managed Java installations."""
    from msm_core.java_manager import get_managed_javas
    return get_managed_javas()


@app.get("/api/v1/java/available", tags=["Java"])
def list_available_java():
    """List available Java versions for download."""
    from msm_core.java_manager import get_available_java_versions

    try:
        return get_available_java_versions()
    except MSMError as e:
        raise handle_msm_error(e)


@app.post("/api/v1/java/install/{version}", tags=["Java"])
def install_java(version: int):
    """Download and install a Java runtime."""
    from msm_core.java_manager import download_java

    try:
        result = download_java(version)
        return result
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/java/recommend/{mc_version}", tags=["Java"])
def recommend_java(mc_version: str):
    """Get recommended Java for a Minecraft version."""
    from msm_core.java_manager import detect_installed_javas, get_best_java_for_version

    javas = detect_installed_javas()
    best = get_best_java_for_version(mc_version, javas)

    if best:
        return {"recommended": best, "mc_version": mc_version}
    else:
        return {"recommended": None, "mc_version": mc_version, "message": "No compatible Java found"}


# ============================================================================
# Server Properties Endpoints
# ============================================================================

class UpdatePropertiesRequest(BaseModel):
    properties: dict


@app.get("/api/v1/servers/{server_id}/properties", tags=["Configuration"])
def get_server_properties(server_id: int):
    """Get server.properties for a server."""
    from msm_core.config_editor import get_server_properties as do_get

    try:
        return do_get(server_id)
    except MSMError as e:
        raise handle_msm_error(e)


@app.patch("/api/v1/servers/{server_id}/properties", tags=["Configuration"])
def update_server_properties(server_id: int, req: UpdatePropertiesRequest):
    """Update server.properties for a server."""
    from msm_core.config_editor import update_server_properties as do_update

    try:
        return do_update(server_id, req.properties)
    except MSMError as e:
        raise handle_msm_error(e)


@app.get("/api/v1/properties/schema", tags=["Configuration"])
def get_properties_schema():
    """Get the server.properties schema with types and defaults."""
    from msm_core.config_editor import get_property_schema
    return get_property_schema()


# ============================================================================
# Server Types and Versions Endpoints
# ============================================================================

@app.get("/api/v1/server-types", tags=["Servers"])
def get_server_types():
    """Get available server types with metadata."""
    from msm_core.installers import get_server_types as do_get_types
    return do_get_types()


@app.get("/api/v1/versions/{server_type}", tags=["Servers"])
def get_versions(server_type: str, include_snapshots: bool = False):
    """Get available versions for a server type.

    Args:
        server_type: Type of server (paper, vanilla, fabric, purpur).
        include_snapshots: Whether to include snapshot/unstable versions.
    """
    from msm_core.installers import get_available_versions

    versions = get_available_versions(server_type, include_snapshots)
    if not versions:
        raise HTTPException(
            status_code=404,
            detail=f"No versions found for server type '{server_type}'"
        )
    return {"versions": versions, "server_type": server_type}


# ============================================================================
# Static Files and SPA Fallback
# ============================================================================

from pathlib import Path
from fastapi.responses import FileResponse, HTMLResponse

# Get the frontend dist directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static assets if frontend is built
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        # Don't serve SPA for API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Try to serve the requested file
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="Frontend not built")
