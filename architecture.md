# Architecture

MSM is designed as a modular, cross-platform application with a clear separation of concerns.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  ┌─────────────────┐              ┌─────────────────────────┐   │
│  │   CLI (msh)     │              │   Web Dashboard         │   │
│  │   Typer + Rich  │              │   React + Vite          │   │
│  └────────┬────────┘              └───────────┬─────────────┘   │
└───────────┼────────────────────────────────────┼────────────────┘
            │                                    │
            ▼                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Web Backend                                │
│                    FastAPI + WebSocket                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │ REST API    │  │ WebSocket   │  │ Auth        │               │
│  │ (50+ routes)│  │ Console     │  │ API Keys    │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                          Core (msm_core)                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│  │ Lifecycle  │ │ Backups    │ │ Plugins    │ │ Scheduler  │     │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│  │ Installers │ │ Java Mgr   │ │ Config Ed  │ │ Services   │     │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                    │
│  │ Database   │ │ Monitor    │ │ API        │                    │
│  └────────────┘ └────────────┘ └────────────┘                    │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                      Platform Adapters                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ Windows         │  │ Linux           │  │ macOS           │   │
│  │ (pywin32)       │  │ (systemd)       │  │ (launchd)       │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     Java Process (Minecraft Server)               │
└───────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Core (`msm_core`)

The heart of the application. Contains OS-agnostic business logic.

| Module | Description |
|--------|-------------|
| `api.py` | High-level API for CLI and web backend |
| `lifecycle.py` | Server process management (start, stop, restart) |
| `installers.py` | Server JAR downloading from PaperMC, Mojang, etc. |
| `backups.py` | Backup creation, restoration, and pruning |
| `plugins.py` | Plugin management with Modrinth/Hangar integration |
| `scheduler.py` | Cron-based task scheduling with background daemon |
| `java_manager.py` | Java detection and Adoptium downloads |
| `config_editor.py` | server.properties editor with schema validation |
| `services.py` | Platform service management (systemd/launchd/NSSM) |
| `monitor.py` | System and process statistics |
| `db.py` | SQLite database with SQLAlchemy ORM |
| `config.py` | Configuration persistence |
| `exceptions.py` | Custom exception hierarchy |

### 2. Platform Adapters (`platform_adapters`)

OS-specific implementations hidden behind a common interface (`PlatformAdapter`).

| Adapter | Platform | Technologies |
|---------|----------|--------------|
| `windows_adapter.py` | Windows | pywin32, PowerShell, NSSM |
| `linux_adapter.py` | Linux | systemd, POSIX signals |
| `macos_adapter.py` | macOS | launchd |

### 3. CLI (`cli`)

Implemented using Typer with Rich console output.

| Subcommand | Description |
|------------|-------------|
| `server` | Server management (create, start, stop, list, etc.) |
| `backup` | Backup operations (create, list, restore, prune) |
| `plugin` | Plugin management (search, install, list, enable) |
| `schedule` | Task scheduling (create, list, enable, delete) |
| `java` | Java runtime management (list, detect, install) |
| `web` | Web dashboard control (start) |

### 4. Web Backend (`web/backend`)

FastAPI application exposing the Core API.

| Module | Description |
|--------|-------------|
| `app.py` | REST endpoints (50+ routes) |
| `ws_console.py` | WebSocket for live console streaming |
| `auth.py` | API key authentication |

### 5. Web Frontend (`web/frontend`)

React + Vite application providing a user-friendly dashboard.

## Database Schema

```
┌─────────────────────┐     ┌─────────────────────┐
│       Server        │     │       Backup        │
├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │────<│ id (PK)             │
│ name                │     │ server_id (FK)      │
│ type                │     │ filename            │
│ version             │     │ size_bytes          │
│ path                │     │ backup_type         │
│ port                │     │ created_at          │
│ memory              │     └─────────────────────┘
│ is_running          │
│ pid                 │     ┌─────────────────────┐
│ java_path           │     │       Plugin        │
│ jvm_args            │     ├─────────────────────┤
│ created_at          │────<│ id (PK)             │
└─────────────────────┘     │ server_id (FK)      │
                            │ name                │
┌─────────────────────┐     │ filename            │
│      Schedule       │     │ source              │
├─────────────────────┤     │ project_id          │
│ id (PK)             │     │ version             │
│ server_id (FK)      │     │ enabled             │
│ action              │     │ installed_at        │
│ cron_expression     │     └─────────────────────┘
│ payload             │
│ enabled             │     ┌─────────────────────┐
│ last_run            │     │       APIKey        │
│ next_run            │     ├─────────────────────┤
│ created_at          │     │ id (PK)             │
└─────────────────────┘     │ name                │
                            │ key_hash            │
                            │ key_prefix          │
                            │ is_active           │
                            │ permissions         │
                            │ created_at          │
                            │ last_used           │
                            └─────────────────────┘
```

## Data Flow

### Starting a Server

1. **User Action**: User clicks "Start" in Web UI or runs `msh server start`
2. **API Layer**: Request reaches `msm_core.api.start_server()`
3. **Lifecycle**:
   - Retrieves server config from database
   - Validates server state (not already running)
   - Calls `PlatformAdapter.start_process()`
4. **Platform Adapter**:
   - Constructs Java command with JVM arguments
   - Spawns process with appropriate flags
   - Captures stdout/stderr for console streaming
5. **Monitoring**:
   - Updates database with PID and running state
   - Streams stdout to WebSocket clients

### Console WebSocket Flow

```
Client                    Server                    Minecraft
  │                         │                          │
  │──── Connect WS ────────>│                          │
  │<─── History ────────────│                          │
  │                         │<──── stdout ─────────────│
  │<─── Output ─────────────│                          │
  │                         │                          │
  │──── Command ───────────>│                          │
  │                         │──── stdin ──────────────>│
  │<─── Ack ────────────────│                          │
```

### Plugin Installation Flow

```
User                    MSM                     Modrinth API
  │                      │                          │
  │── Search "plugin" ──>│                          │
  │                      │── GET /search ──────────>│
  │                      │<── Results ──────────────│
  │<── Plugin List ──────│                          │
  │                      │                          │
  │── Install "xyz" ────>│                          │
  │                      │── GET /project/xyz ─────>│
  │                      │<── Version Info ─────────│
  │                      │── GET /download ────────>│
  │                      │<── JAR file ─────────────│
  │<── Success ──────────│                          │
```

## External API Integrations

| API | Endpoint | Purpose |
|-----|----------|---------|
| Modrinth | `https://api.modrinth.com/v2` | Plugin search and downloads |
| Hangar | `https://hangar.papermc.io/api/v1` | Plugin search and downloads |
| Adoptium | `https://api.adoptium.net/v3` | Java runtime downloads |
| PaperMC | `https://api.papermc.io/v2` | Paper/Velocity server JARs |
| Mojang | `https://launchermeta.mojang.com` | Vanilla server JARs |

## Platform Services

MSM can create background services to run Minecraft servers.

### Linux (systemd)

```ini
[Unit]
Description=Minecraft Server - {name}
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={server_path}
ExecStart={java_path} {jvm_args} -jar {jar_name} nogui
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### macOS (launchd)

```xml
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.msm.{name}</string>
    <key>ProgramArguments</key>
    <array>...</array>
    <key>WorkingDirectory</key>
    <string>{server_path}</string>
</dict>
</plist>
```

### Windows (NSSM)

Generates a batch script that uses NSSM to install the server as a Windows service.

## Directory Structure

```
msm/
├── msm_core/               # Core business logic
│   ├── __init__.py
│   ├── api.py              # High-level API
│   ├── lifecycle.py        # Process management
│   ├── installers.py       # JAR downloading
│   ├── backups.py          # Backup system
│   ├── plugins.py          # Plugin manager
│   ├── scheduler.py        # Task scheduler
│   ├── java_manager.py     # Java management
│   ├── config_editor.py    # Properties editor
│   ├── services.py         # Service management
│   ├── monitor.py          # Statistics
│   ├── db.py               # Database
│   ├── config.py           # Configuration
│   └── exceptions.py       # Exceptions
├── platform_adapters/      # Platform-specific code
│   ├── __init__.py
│   ├── base.py             # Abstract base class
│   ├── windows_adapter.py
│   ├── linux_adapter.py
│   └── macos_adapter.py
├── cli/                    # CLI application
│   ├── __init__.py
│   └── main.py             # Typer commands
├── web/
│   ├── backend/            # FastAPI application
│   │   ├── __init__.py
│   │   ├── app.py          # REST endpoints
│   │   ├── ws_console.py   # WebSocket
│   │   └── auth.py         # Authentication
│   └── frontend/           # React application
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── README.md
```
