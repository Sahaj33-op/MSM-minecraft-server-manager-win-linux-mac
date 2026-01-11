"""Pydantic schemas/DTOs for MSM.

These schemas provide clean data transfer between API layers,
avoiding SQLAlchemy DetachedInstanceError issues.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ServerBase(BaseModel):
    """Base server properties."""
    name: str
    type: str
    version: str
    port: int
    memory: str


class ServerCreate(ServerBase):
    """Schema for creating a server."""
    pass


class ServerUpdate(BaseModel):
    """Schema for updating a server."""
    memory: Optional[str] = None
    port: Optional[int] = None
    java_path: Optional[str] = None
    jvm_args: Optional[str] = None


class ServerResponse(ServerBase):
    """Schema for server response data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    is_running: bool = False
    pid: Optional[int] = None
    java_path: Optional[str] = None
    jvm_args: Optional[str] = None
    created_at: Optional[datetime] = None
    last_started: Optional[datetime] = None
    last_stopped: Optional[datetime] = None


class ServerSummary(BaseModel):
    """Lightweight server summary for lists."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    version: str
    port: int
    memory: str
    is_running: bool = False
    pid: Optional[int] = None


class BackupBase(BaseModel):
    """Base backup properties."""
    server_id: int
    backup_type: str = "manual"


class BackupResponse(BaseModel):
    """Schema for backup response data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    filename: str
    path: str
    size_bytes: int
    backup_type: str
    created_at: datetime


class PluginBase(BaseModel):
    """Base plugin properties."""
    name: str
    source: str  # 'modrinth', 'hangar', 'url'


class PluginResponse(BaseModel):
    """Schema for plugin response data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    name: str
    version: Optional[str] = None
    source: str
    source_id: Optional[str] = None
    filename: str
    enabled: bool = True
    installed_at: datetime


class ScheduleBase(BaseModel):
    """Base schedule properties."""
    action: str  # 'backup', 'restart', 'stop', 'command'
    cron: str
    command: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Schema for schedule response data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    action: str
    cron: str
    command: Optional[str] = None
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    created_at: datetime


class JavaRuntime(BaseModel):
    """Schema for Java runtime information."""
    path: str
    version: str
    vendor: Optional[str] = None
    is_managed: bool = False


class SystemStats(BaseModel):
    """Schema for system statistics."""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    server_count: int
    running_servers: int
