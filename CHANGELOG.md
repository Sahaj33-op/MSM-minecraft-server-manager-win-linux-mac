# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
