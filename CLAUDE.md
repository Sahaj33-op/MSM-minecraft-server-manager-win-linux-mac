# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSM (Minecraft Server Manager) is a cross-platform (Windows, Linux, macOS) local Minecraft server host with a CLI (`msh`) and React + FastAPI web dashboard.

## Common Commands

### Python Backend
```bash
poetry install                    # Install dependencies
poetry run msh --help             # Run CLI
poetry run msh server create --name my-server --type paper --version 1.20.4
poetry run msh web start          # Start web UI (http://localhost:5000)
poetry run uvicorn web.backend.app:app --reload  # Dev backend only
```

### CLI Subcommands
```bash
# Server management
poetry run msh server list
poetry run msh server start <name>
poetry run msh server stop <name>

# Backup management
poetry run msh backup create <server>
poetry run msh backup list [server]
poetry run msh backup restore <id>

# Plugin management
poetry run msh plugin search "query"
poetry run msh plugin install <server> <project>
poetry run msh plugin list <server>

# Schedule management
poetry run msh schedule create <server> --action backup --cron "0 4 * * *"
poetry run msh schedule list

# Java management
poetry run msh java list
poetry run msh java install 21
poetry run msh java detect
```

### Frontend
```bash
cd web/frontend
npm install
npm run dev      # Dev server
npm run build    # Production build
npm run lint     # ESLint
```

### Testing
```bash
poetry run pytest                    # All tests
poetry run pytest tests/unit         # Unit tests only
poetry run pytest tests/integration  # Integration tests only
poetry run pytest tests/unit/test_config.py  # Single test file
```

### Code Quality
```bash
poetry run pre-commit install    # Setup hooks (do this once)
poetry run black .               # Format Python
poetry run ruff check --fix .    # Lint Python
poetry run mypy .                # Type check (strict mode)
```

## Architecture

### Component Layers
1. **`msm_core/`** - OS-agnostic business logic
   - `api.py` - Core API exposed to CLI and web backend
   - `lifecycle.py` - Server process management (start/stop/restart)
   - `installers.py` - Server jar downloading and verification
   - `db.py` - SQLite database with Server, Plugin, Backup, Schedule, APIKey models
   - `config.py` - Configuration persistence
   - `backups.py` - Backup creation, restoration, and pruning
   - `plugins.py` - Plugin management (Modrinth/Hangar API integration)
   - `scheduler.py` - Cron-based task scheduling with background daemon
   - `java_manager.py` - Java runtime detection and Adoptium downloads
   - `config_editor.py` - server.properties editor with schema validation
   - `services.py` - Platform service management (systemd/launchd/NSSM)
   - `monitor.py` - System and process statistics
   - `exceptions.py` - Custom exception hierarchy

2. **`platform_adapters/`** - OS-specific implementations behind `PlatformAdapter` ABC
   - `base.py` - Abstract base class defining the interface
   - `windows_adapter.py` - Windows (pywin32/PowerShell)
   - `linux_adapter.py` - Linux (systemd/POSIX signals)
   - `macos_adapter.py` - macOS (launchd)

3. **`cli/`** - Typer-based CLI (`msh` command)
   - `main.py` - CLI with subcommands: server, backup, plugin, schedule, java, web

4. **`web/backend/`** - FastAPI application
   - `app.py` - REST endpoints (50+ endpoints for all features)
   - `ws_console.py` - WebSocket for live console streaming
   - `auth.py` - API key authentication with secure hashing

5. **`web/frontend/`** - React + Vite + TailwindCSS dashboard

### Database Models
- **Server**: id, name, type, version, path, port, memory, is_running, pid, java_path, jvm_args
- **Plugin**: id, server_id, name, filename, source, project_id, version, enabled
- **Backup**: id, server_id, filename, size_bytes, backup_type, created_at
- **Schedule**: id, server_id, action, cron_expression, enabled, last_run, next_run
- **APIKey**: id, name, key_hash, key_prefix, is_active, permissions

### External APIs
- **Modrinth API**: `https://api.modrinth.com/v2` - Plugin search and downloads
- **Hangar API**: `https://hangar.papermc.io/api/v1` - Plugin search and downloads
- **Adoptium API**: `https://api.adoptium.net/v3` - Java runtime downloads
- **PaperMC API**: `https://api.papermc.io/v2` - Paper/Velocity server downloads

### Data Flow
User action (Web UI or CLI) → Core API (`msm_core`) → Platform Adapter → Java process

### Adding a Platform Adapter
1. Create new file in `platform_adapters/`
2. Inherit from `PlatformAdapter` in `platform_adapters/base.py`
3. Implement all abstract methods
4. Update `msm_core/utils.py` to select adapter based on `sys.platform`

## Code Style

- **Python**: Black, Ruff, Isort, Mypy (strict mode enabled)
- **Frontend**: ESLint, TypeScript strict
- **Commits**: Use Conventional Commits format

## Key Implementation Patterns

### Database Sessions
Use context manager pattern for all database operations:
```python
from msm_core.db import get_session

with get_session() as session:
    server = session.query(Server).filter(Server.id == server_id).first()
    # Changes are auto-committed on context exit
```

### API Key Authentication
```python
from web.backend.auth import verify_api_key

@app.get("/api/v1/protected")
def protected_endpoint(key_info: dict = Depends(verify_api_key)):
    return {"authenticated": True}
```

### Cron Scheduling
```python
from croniter import croniter
from datetime import datetime

cron = croniter("0 4 * * *", datetime.now())
next_run = cron.get_next(datetime)
```

## Reference Implementations

The `docs/` folder contains source code from competitor projects for implementation reference:

| Folder | Project | Tech Stack | Reference For |
|--------|---------|------------|---------------|
| `docs/Fork-main/` | [Fork](https://github.com/ForkGG/Fork) | C# / .NET 6 / Blazor | Discord bot, plugin manager, UI/UX patterns |
| `docs/MCSManager-master/` | [MCSManager](https://github.com/MCSManager/MCSManager) | TypeScript / Node.js | Distributed architecture, Docker integration, multi-user permissions |
| `docs/pterodactyl-panel-1.0-develop/` | [Pterodactyl](https://github.com/pterodactyl/panel) | PHP / Laravel / React | Enterprise patterns, Docker isolation, Wings daemon, REST API design |

### When to Reference

- **Server installers**: Check how MCSManager/Pterodactyl fetch server JARs from PaperMC/Mojang APIs
- **Console streaming**: Fork and Pterodactyl have WebSocket implementations for live console
- **Plugin management**: Fork has built-in plugin manager with search
- **Background services**: Pterodactyl Wings daemon shows service architecture
- **Authentication**: Pterodactyl has token-based auth with granular privileges
- **Discord integration**: Fork has built-in Discord bot for server control
