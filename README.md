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
| **Web Dashboard** | Modern React interface with real-time server monitoring and console streaming |
| **CLI (`msh`)** | Full-featured command-line interface for automation and scripting |
| **Multi-Server** | Manage multiple Minecraft servers from a single installation |
| **Server Types** | Support for Paper, Fabric, Vanilla, and other server distributions |
| **Backups** | Automated and manual backup management |
| **Monitoring** | Live CPU/RAM usage tracking and server console output |

## Requirements

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core application runtime |
| Node.js | 18+ | Frontend build toolchain |
| Java | 17+ | Minecraft server execution |

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/msm.git
cd msm
```

### 2. Install Backend Dependencies

```bash
pip install poetry
poetry install
```

### 3. Build the Frontend

```bash
cd web/frontend
npm install
npm run build
cd ../..
```

## Usage

### Web Dashboard

Launch the web interface:

```bash
poetry run msh web start
```

Access the dashboard at **http://localhost:5000**

### Command-Line Interface

```bash
# View available commands
poetry run msh --help

# Create a new server
poetry run msh server create --name survival --type paper --version 1.20.4

# Start a server
poetry run msh server start survival

# Stop a server
poetry run msh server stop survival

# List all servers
poetry run msh server list

# View server status
poetry run msh server status survival
```

## Project Structure

```
msm/
├── msm_core/           # Core business logic (OS-agnostic)
├── platform_adapters/  # Platform-specific implementations
├── cli/                # Typer-based CLI application
├── web/
│   ├── backend/        # FastAPI REST API + WebSocket server
│   └── frontend/       # React + Vite dashboard
└── tests/              # Unit and integration tests
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

## Documentation

- [Architecture Overview](architecture.md) - System design and component structure
- [Contributing Guide](CONTRIBUTING.md) - Development workflow and guidelines
- [Changelog](CHANGELOG.md) - Version history and release notes
- [Developer Notes](DEV_NOTES.md) - Technical notes and tips

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
