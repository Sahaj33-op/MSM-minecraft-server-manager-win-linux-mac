# MSM - Minecraft Server Manager

A production-ready, cross-platform Minecraft server management solution featuring a powerful CLI and modern web dashboard.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

## Overview

MSM simplifies hosting and managing local Minecraft servers. Whether you prefer command-line tools or a graphical interface, MSM provides both through its `msh` CLI and React-based web dashboard.

### Key Features

| Feature | Description |
|---------|-------------|
| **Cross-Platform** | Native support for Windows, Linux, and macOS with platform-specific optimizations |
| **Web Dashboard** | Modern dark-themed React interface with real-time server monitoring and console streaming |
| **CLI (`msh`)** | Full-featured command-line interface for automation and scripting |
| **Multi-Server** | Manage multiple Minecraft servers from a single installation |
| **Server Types** | Support for Paper, Fabric, Vanilla, Purpur, and other server distributions |
| **Backup System** | Automated and manual backup management with restore and pruning |
| **Plugin Manager** | Search and install plugins from Modrinth and Hangar |
| **Scheduler** | Cron-based task scheduling for backups, restarts, and commands |
| **Java Manager** | Auto-detect installed Java runtimes and download from Adoptium |
| **Monitoring** | Live CPU/RAM usage tracking and server console output |
| **Robustness** | Automatic state recovery, WebSocket auto-reconnect, and comprehensive error handling |
| **API** | RESTful API with health checks and optional authentication for custom integrations |

## Requirements

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core application runtime |
| Node.js | 18+ | Frontend build toolchain |
| Java | 17+ | Minecraft server execution (can be auto-installed) |

## Installation

### Quick Install

```bash
pip install poetry
git clone https://github.com/Sahaj33-op/MSM-minecraft-server-manager-win-linux-mac.git
cd MSM-minecraft-server-manager-win-linux-mac
poetry install
```

### Build the Frontend (Optional)

```bash
cd web/frontend
npm install
npm run build
cd ../..
```

## Usage

### Quick Start

```bash
# Create a new Paper server
poetry run msh server create --name survival --type paper --version 1.20.4

# Start the server
poetry run msh server start survival

# View server status
poetry run msh server status survival
```

### Web Dashboard

Launch the web interface:

```bash
poetry run msh web start
```

Access the dashboard at **http://localhost:5000**

### Command-Line Interface

#### Server Management

```bash
# View available commands
poetry run msh --help

# Create a new server
poetry run msh server create --name survival --type paper --version 1.20.4

# Start/stop/restart a server
poetry run msh server start survival
poetry run msh server stop survival
poetry run msh server restart survival

# List all servers
poetry run msh server list

# View detailed server status
poetry run msh server status survival

# Import an existing server
poetry run msh server import /path/to/server --name imported-server

# Delete a server
poetry run msh server delete survival

# Send console commands
poetry run msh server cmd survival "say Hello World"

# Attach to server console (interactive)
poetry run msh server console survival
```

#### Backup Management

```bash
# Create a backup
poetry run msh backup create survival

# Create a backup with server stopped first
poetry run msh backup create survival --stop

# List backups
poetry run msh backup list
poetry run msh backup list survival

# Restore from backup
poetry run msh backup restore 1

# Delete a backup
poetry run msh backup delete 1

# Prune old backups (keep 5 most recent)
poetry run msh backup prune --keep 5
```

#### Plugin Management

```bash
# Search for plugins on Modrinth
poetry run msh plugin search "essentials"

# Search on Hangar
poetry run msh plugin search "vault" --source hangar

# Install a plugin from Modrinth
poetry run msh plugin install survival essentialsx

# Install from URL
poetry run msh plugin install survival https://example.com/plugin.jar

# List installed plugins
poetry run msh plugin list survival

# Enable/disable plugins
poetry run msh plugin enable 1
poetry run msh plugin disable 1

# Check for plugin updates
poetry run msh plugin updates survival

# Uninstall a plugin
poetry run msh plugin uninstall 1
```

#### Scheduled Tasks

```bash
# Schedule daily backup at 4 AM
poetry run msh schedule create survival --action backup --cron "0 4 * * *"

# Schedule weekly restart on Sundays at 3 AM
poetry run msh schedule create survival --action restart --cron "0 3 * * 0"

# List schedules
poetry run msh schedule list

# Enable/disable schedules
poetry run msh schedule enable 1
poetry run msh schedule disable 1

# Delete a schedule
poetry run msh schedule delete 1
```

#### Java Management

```bash
# List detected Java installations
poetry run msh java list

# Show MSM-managed Java only
poetry run msh java list --managed

# Show recommended Java for different MC versions
poetry run msh java detect

# Show available Java versions for download
poetry run msh java available

# Download and install Java
poetry run msh java install 21

# Remove a managed Java installation
poetry run msh java remove /path/to/java
```

## API Reference

MSM exposes a REST API at `http://localhost:5000/api/v1/`. Interactive documentation is available at `/docs`.

### Endpoints Overview

| Category | Endpoints |
|----------|-----------|
| **Servers** | `GET/POST /servers`, `GET/PATCH/DELETE /servers/{id}`, `POST /servers/{id}/start\|stop\|restart` |
| **Console** | `GET /servers/{id}/console/history`, `POST /servers/{id}/console/command`, `WS /servers/{id}/console/ws` |
| **Backups** | `GET/POST /servers/{id}/backups`, `GET/DELETE /backups/{id}`, `POST /backups/{id}/restore` |
| **Plugins** | `GET /plugins/search`, `GET/POST /servers/{id}/plugins`, `DELETE /plugins/{id}` |
| **Schedules** | `GET/POST /servers/{id}/schedules`, `GET/PATCH/DELETE /schedules/{id}` |
| **Java** | `GET /java/installed`, `GET /java/available`, `POST /java/install/{version}` |
| **Config** | `GET/PATCH /servers/{id}/properties`, `GET /properties/schema` |
| **System** | `GET /stats`, `GET /health` |

## Project Structure

```
msm/
├── msm_core/               # Core business logic (OS-agnostic)
│   ├── api.py              # Core API for CLI and web
│   ├── lifecycle.py        # Server process management
│   ├── console.py          # Console I/O and process monitoring
│   ├── background.py       # Background tasks and state sync
│   ├── installers.py       # Server JAR downloading
│   ├── backups.py          # Backup system
│   ├── plugins.py          # Plugin manager (Modrinth/Hangar)
│   ├── scheduler.py        # Cron-based task scheduler
│   ├── java_manager.py     # Java runtime management
│   ├── config_editor.py    # server.properties editor
│   ├── monitor.py          # System resource monitoring
│   ├── services.py         # Platform service management
│   ├── db.py               # SQLite database
│   ├── config.py           # Configuration persistence
│   └── exceptions.py       # Custom exception classes
├── platform_adapters/      # Platform-specific implementations
│   ├── base.py             # Abstract base class
│   ├── windows_adapter.py  # Windows support
│   ├── linux_adapter.py    # Linux support
│   └── macos_adapter.py    # macOS support
├── cli/                    # Typer-based CLI application
│   └── main.py             # CLI commands
├── web/
│   ├── backend/            # FastAPI REST API + WebSocket
│   │   ├── app.py          # API endpoints
│   │   ├── auth.py         # API authentication
│   │   └── ws_console.py   # Console WebSocket with auto-reconnect
│   └── frontend/           # React + Vite + TailwindCSS dashboard
│       └── src/
│           ├── components/ # Reusable UI components
│           ├── pages/      # Page components
│           ├── hooks/      # Custom React hooks
│           └── types/      # TypeScript type definitions
└── tests/                  # Unit and integration tests
```

## Development

### Running in Development Mode

**Backend:**
```bash
poetry run uvicorn web.backend.app:app --reload
```

**Frontend:**
```bash
cd web/frontend
npm run dev
```

### Running Tests

```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit

# Integration tests only
poetry run pytest tests/integration

# With verbose output
poetry run pytest -v
```

### Code Quality

```bash
# Setup pre-commit hooks (first time only)
poetry run pre-commit install

# Manual formatting and linting
poetry run black .
poetry run ruff check --fix .
poetry run mypy .
```

## Configuration

MSM stores its configuration and data in platform-specific locations:

| Platform | Data Directory |
|----------|----------------|
| Windows | `%APPDATA%\msm` |
| Linux | `~/.local/share/msm` |
| macOS | `~/Library/Application Support/msm` |

## Platform Services

MSM can create background services to run Minecraft servers:

| Platform | Service Type | Command |
|----------|--------------|---------|
| Linux | systemd user service | `systemctl --user start msm-servername` |
| macOS | launchd agent | `launchctl start com.msm.servername` |
| Windows | NSSM service | Run generated `install_service.bat` |

## Documentation

- [Architecture Overview](architecture.md) - System design and component structure
- [Contributing Guide](CONTRIBUTING.md) - Development workflow and guidelines
- [Changelog](CHANGELOG.md) - Version history and release notes

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Links

- **Repository**: https://github.com/Sahaj33-op/MSM-minecraft-server-manager-win-linux-mac
- **Issues**: https://github.com/Sahaj33-op/MSM-minecraft-server-manager-win-linux-mac/issues
