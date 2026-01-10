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
   - `lifecycle.py` - Server process management (start/stop/restart)
   - `installers.py` - Server jar downloading and verification
   - `db.py` - SQLite database for server metadata
   - `config.py` - Configuration persistence
   - `api.py` - Core API exposed to CLI and web backend

2. **`platform_adapters/`** - OS-specific implementations behind `PlatformAdapter` ABC
   - `base.py` - Abstract base class defining the interface
   - `windows_adapter.py` - Windows (pywin32/PowerShell)
   - `linux_adapter.py` - Linux (systemd/POSIX signals)
   - `macos_adapter.py` - macOS (launchd)

3. **`cli/`** - Typer-based CLI (`msh` command)

4. **`web/backend/`** - FastAPI application
   - `app.py` - REST endpoints for server management
   - `ws_console.py` - WebSocket for live console streaming

5. **`web/frontend/`** - React + Vite + TailwindCSS dashboard

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
