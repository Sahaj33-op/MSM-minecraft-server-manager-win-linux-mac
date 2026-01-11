# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-01-11

### Security

- **Root Privilege Protection** - Services cannot be created when running as root/Administrator
  - Prevents Minecraft servers from running with elevated privileges
  - Protects against malicious plugins compromising the system
- **Path Traversal Prevention** - Server deletion validates paths are within MSM data directory
  - Blocks attempts to delete files outside the servers folder
  - Validates resolved paths to handle symlinks and `..` attacks
- **Improved Server Name Validation** - Strict alphanumeric validation with path separator blocking

### Changed

- **State Synchronization** - OS process table is now the source of truth for server status
  - `list_servers` verifies actual running state against OS on every call
  - `get_server_status` reconciles DB state with OS reality
  - Automatic correction when database and OS states differ
- **Jar File Detection** - Smarter heuristic for finding server JAR files
  - Checks for `Main-Class` manifest entries to identify runnable JARs
  - Falls back to largest JAR file (server JARs are typically larger than libraries)
  - Expanded list of common server jar names (purpur, spigot, minecraft_server)

### Technical

- Added `msm_core/schemas.py` with Pydantic DTOs for clean data transfer
- Replaced detached ORM object pattern with `ServerResponse.model_validate()`
- Added `_is_running_as_root()` and `_check_root_safety()` security helpers
- Added `_validate_path_is_safe_for_deletion()` path containment check

## [0.3.0] - 2026-01-11

### Added

#### Robustness & Reliability
- **Background Task Manager** - Periodic state sync every 10 seconds
- **Dead Console Cleanup** - Automatic cleanup of stale console entries every 30 seconds
- **Port Conflict Detection** - Pre-start port availability checking with process identification
- **Process Monitoring** - Automatic detection when servers stop via console commands
- **Exit Callbacks** - Database auto-update when server processes terminate
- **Graceful Shutdown** - Proper cleanup of all background tasks on application exit

#### WebSocket Improvements
- Auto-reconnect with exponential backoff (up to 5 attempts)
- Server stopped notification handling
- Heartbeat keep-alive support
- Connection state tracking
- Intentional vs unintentional disconnect handling

#### API Resilience
- `fetchWithRetry` helper with configurable retry attempts
- Exponential backoff between retries
- Graceful degradation on network errors
- Health check endpoint with uptime tracking

### Changed

#### Modern Dark UI Theme
- Deeper black color palette (#0a0a0f background)
- Subtle ambient glow effects with radial gradients
- Glassmorphism card effects with backdrop blur
- Modern button animations (lift, glow, gradient overlay)
- Staggered card entrance animations
- Pulsing status indicators for online servers
- Progress bar glow effects for warning/critical levels
- Minimalistic sidebar with server status indicator
- Compact stats bar with vertical dividers
- Thinner scrollbars with transparent tracks
- Updated typography with tighter letter-spacing

#### UI Components
- ServerCard with running state indicator bar
- StatsBar with loading skeleton state
- Sidebar with live server status dot
- Dashboard with staggered card animations
- Improved button hover/active states

### Fixed
- Port conflict crashes on server start
- Server status not updating when stopped via `/stop` command
- WebSocket disconnects not triggering reconnection
- Memory leak in console output subscriptions
- Race conditions in process monitoring

### Technical
- Added `PortInUseError` exception class
- Added `background.py` module for periodic tasks
- Enhanced platform adapters with proper process wait on stop
- Improved WebSocket manager with loop tracking
- Added comprehensive TypeScript types for console messages

## [0.2.0] - 2025-01-11

### Added

#### Phase 1: Core Infrastructure
- Complete server lifecycle management (start/stop/restart)
- Server process monitoring with PID tracking
- Server state synchronization on startup
- WebSocket-based live console streaming
- Console command sending to running servers
- Console history retrieval
- Server import functionality for existing servers
- Platform adapters for Windows, Linux, and macOS

#### Phase 2: Backup & Plugin System
- **Backup Management**
  - Create compressed tar.gz backups of server directories
  - List all backups or filter by server
  - Restore servers from backup files
  - Delete individual backups
  - Prune old backups (keep by count or days)
  - Optional server stop before backup
  - Backup types: manual, scheduled, pre-update

- **Plugin Management**
  - Search plugins on Modrinth API
  - Search plugins on Hangar API
  - Install plugins from Modrinth by project ID
  - Install plugins from direct URL
  - List installed plugins per server
  - Enable/disable plugins (move to .disabled extension)
  - Uninstall plugins with file deletion
  - Check for plugin updates

- **Scheduled Tasks**
  - Cron-based task scheduling with croniter
  - Supported actions: backup, restart, stop, command
  - Enable/disable schedules
  - Background daemon thread for schedule execution
  - Next run time calculation

- **Java Runtime Management**
  - Auto-detect installed Java runtimes on all platforms
  - Common installation path scanning
  - Java version parsing from `java -version` output
  - Adoptium API integration for downloads
  - Download and extract Java binaries
  - Track MSM-managed Java installations
  - Recommend Java version for Minecraft versions

#### Phase 3: Web API Extensions
- 50+ REST API endpoints covering all features
- Server CRUD operations via API
- Backup management endpoints
- Plugin management endpoints
- Schedule management endpoints
- Java management endpoints
- Server properties configuration endpoints
- System statistics endpoint
- Health check endpoint

#### Phase 4: Configuration & Services
- **Server Properties Editor**
  - Read/write server.properties files
  - Full property schema with types, defaults, descriptions
  - Property validation against schema
  - Batch property updates

- **API Authentication**
  - API key generation with secure random tokens
  - SHA-256 key hashing for storage
  - Key prefix for identification
  - Key revocation and deletion
  - Permission-based access control
  - FastAPI security dependencies

- **Platform Services**
  - Systemd service generation for Linux
  - Launchd plist generation for macOS
  - NSSM batch script generation for Windows
  - Service removal utilities
  - Service status checking

### CLI Commands Added
- `msh backup create|list|restore|delete|prune`
- `msh plugin search|install|list|enable|disable|uninstall|updates`
- `msh schedule create|list|enable|disable|delete`
- `msh java list|detect|available|install|remove`

### Technical Improvements
- SQLAlchemy 2.0 Mapped column syntax
- Context manager pattern for database sessions
- Comprehensive exception hierarchy
- Rich console output for CLI
- Proper error handling throughout

## [0.1.0] - 2025-12-01

### Added
- Initial project scaffold
- Core architecture design with platform abstraction
- Basic CLI structure with Typer
- Web backend skeleton with FastAPI
- Web frontend skeleton with React + Vite
- SQLite database schema for servers
- Server JAR installers for Paper, Fabric, Vanilla, Purpur
- Basic server creation workflow
