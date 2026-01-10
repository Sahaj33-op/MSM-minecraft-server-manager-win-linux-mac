# Architecture

MSM is designed as a modular, cross-platform application with a clear separation of concerns.

## Components

### 1. Core (`msm_core`)
The heart of the application. Contains business logic that is OS-agnostic.
- **Lifecycle**: Manages server processes (start, stop, restart).
- **Installers**: Handles downloading and verifying server jars.
- **Config**: Manages configuration persistence.
- **DB**: SQLite database for storing server metadata.

### 2. Platform Adapters (`platform_adapters`)
OS-specific implementations hidden behind a common interface (`PlatformAdapter`).
- **Windows**: Uses `pywin32` / PowerShell for service management.
- **Linux**: Uses `systemd` and standard POSIX signals.
- **macOS**: Uses `launchd`.

### 3. CLI (`cli`)
Implemented using `Typer`. Provides a command-line interface to the Core API.

### 4. Web Backend (`web/backend`)
FastAPI application that exposes the Core API via REST and WebSockets.
- **REST**: Server management, stats.
- **WebSockets**: Live console streaming.

### 5. Web Frontend (`web/frontend`)
React + Vite application. Communicates with the backend to provide a user-friendly dashboard.

## Data Flow

1.  **User Action**: User clicks "Start" in Web UI.
2.  **Frontend**: Sends `POST /api/v1/servers/{id}/start` to Backend.
3.  **Backend**: Calls `msm_core.lifecycle.start_server(id)`.
4.  **Core**:
    - Retrieves server config from DB.
    - Calls `PlatformAdapter.start_process()`.
5.  **Adapter**: Spawns the Java process with appropriate flags.
6.  **Monitoring**: Core monitors the process and streams stdout to the WebSocket.

## Directory Structure

See `Prompt.md` for the detailed directory tree.
