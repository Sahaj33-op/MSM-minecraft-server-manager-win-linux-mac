# MSM: The Complete Battle Plan

## Strategic Product Document v1.0

---

# Part 1: Vision & Mission

## The Problem

Managing Minecraft servers in 2025 is unnecessarily painful:

| User Type | Current Pain |
|-----------|--------------|
| **Home User** | Pterodactyl needs Docker + PHP + MySQL + Wings—just to play with friends |
| **Sysadmin** | Fork is Windows-only, Crafty has no CLI, everything needs a GUI |
| **Developer** | No CI/CD integration, can't automate plugin testing |
| **VPS User** | Most tools need 500MB+ RAM just for the panel |
| **Mac/Linux User** | Fork doesn't exist, Pterodactyl is overkill |

## The Vision

**"Make Minecraft server hosting as simple as `git`."**

```bash
# This is all it should take
pip install msm
msh server create --name survival --type paper
msh server start survival
```

## The Mission

Build the **#1 cross-platform Minecraft server manager** that:
- Installs in one command
- Works identically on Windows, Linux, and macOS
- Offers both CLI power and web convenience
- Runs on a Raspberry Pi or a datacenter
- Has an API that developers actually want to use

---

# Part 2: Market Analysis

## Competitive Landscape

```
                        COMPLEXITY
                             ↑
                             │
                             │  Pterodactyl ●
                             │  (Enterprise)
                             │
                             │       MCSManager ●
                             │         ● Paid Hosting
                             │       (Distributed)
                             │           (Apex, Shockbyte)
                             │
                             │       Crafty ●
                             │       (Web Panel)
                             │
                        ┌────┼────┐
                        │  ● │    │
                        │ MSM│    │  ← OPPORTUNITY GAP
                        │    │    │
                        └────┼────┘
                             │       Fork ●
                             │       (Windows)
                             │
                             │  Manual Scripts ●
                             │
    ─────────────────────────┼─────────────────────────→ POWER
    SIMPLE                                      ADVANCED
```

## Competitor Deep Dive

### Pterodactyl
```
Strengths:
├── Industry standard for hosting companies
├── Docker isolation, multi-tenant
├── Beautiful UI, active development
└── Huge community, "eggs" ecosystem

Weaknesses:
├── Requires: PHP + MySQL + Redis + Docker + Wings
├── Minimum 512MB RAM just for panel
├── Complex installation (multiple guides needed)
├── Overkill for personal/small team use
└── No real CLI interface
```

### MCSManager
```
Strengths:
├── Distributed architecture
├── Supports Steam games too
├── Good for hosting businesses
└── Active Chinese + international community

Weaknesses:
├── Node.js dependency
├── Complex multi-daemon setup
├── Distributed = more failure points
└── Documentation gaps in English
```

### Crafty Controller
```
Strengths:
├── Python-based (like us)
├── Good feature set
├── Mobile PWA
└── 50k+ installations

Weaknesses:
├── No CLI - GUI only
├── No automation/scripting support
├── Heavier resource usage
└── Complex initial setup
```

### Fork
```
Strengths:
├── Beautiful native Windows app
├── Discord bot built-in
├── Plugin manager
└── Great UX for casual users

Weaknesses:
├── Windows ONLY (fatal flaw)
├── No CLI
├── No headless operation
├── v2 "not production ready" for years
└── Can't run on VPS/cloud
```

## Market Opportunity

| Segment | Size | Current Solution | MSM Opportunity |
|---------|------|------------------|-----------------|
| Home Users (Windows) | Large | Fork, Crafty | Lower complexity |
| Home Users (Mac/Linux) | Medium | Manual/Crafty | **UNDERSERVED** |
| VPS/Cloud Hosting | Large | Pterodactyl | **MASSIVE OPPORTUNITY** |
| Developers/CI-CD | Small | Nothing | **BLUE OCEAN** |
| Raspberry Pi/ARM | Growing | Manual | **UNDERSERVED** |
| Sysadmins | Medium | Scripts/Pterodactyl | CLI-first approach |

**Total Addressable Market:** Millions of Minecraft server operators worldwide
**Serviceable Market:** Those who want simple, cross-platform, scriptable solution
**Beachhead:** Linux VPS users + Mac users + automation-focused developers

---

# Part 3: Product Strategy

## Core Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                     MSM DESIGN PRINCIPLES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SIMPLE FIRST                                                 │
│     If it can't be done in one command, redesign it             │
│                                                                  │
│  2. CLI IS THE API                                               │
│     Every feature works from terminal first, GUI second          │
│                                                                  │
│  3. NATIVE, NOT ABSTRACTED                                       │
│     Platform adapters, not Docker everywhere                     │
│                                                                  │
│  4. MINIMAL DEPENDENCIES                                         │
│     Python + SQLite. No external database. No Docker required.   │
│                                                                  │
│  5. DEVELOPER EXPERIENCE                                         │
│     Great docs, great API, great error messages                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## User Personas

### Persona 1: "Weekend Warrior" (Primary)
```
Name: Alex, 28
Role: Software developer who games on weekends
Setup: Gaming PC (Windows) + Raspberry Pi (Linux)
Needs:
├── Quick server for friends (< 5 minutes)
├── Works on both their machines
├── Doesn't want to learn new tools
└── Occasional automation for restarts

Quote: "I just want to play, not become a sysadmin"
```

### Persona 2: "Terminal Guru" (Primary)
```
Name: Sam, 35
Role: DevOps engineer
Setup: Multiple VPS instances, SSH everywhere
Needs:
├── CLI that doesn't suck
├── Scriptable, automatable
├── Low resource usage
├── SSH-friendly (no GUI required)
└── Integrates with existing tools

Quote: "If I can't pipe it to grep, I don't want it"
```

### Persona 3: "Plugin Developer" (Secondary)
```
Name: Jordan, 22
Role: Minecraft plugin developer
Setup: Dev machine + CI/CD pipeline
Needs:
├── Spin up test servers in CI
├── Automated plugin deployment
├── Multiple MC versions simultaneously
└── API for custom tooling

Quote: "I need to test my plugin on 10 versions automatically"
```

### Persona 4: "Small Host" (Future)
```
Name: Taylor, 30
Role: Runs small hosting for community
Setup: Dedicated server, 5-10 customers
Needs:
├── Multi-server management
├── Resource isolation
├── Basic multi-user access
└── Reliable backups

Quote: "Pterodactyl is overkill, but I need more than Fork"
```

---

# Part 4: Technical Architecture

## Current State (Honest Assessment)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT IMPLEMENTATION STATUS                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ DONE (Solid Foundation)                                      │
│  ├── Architecture: Core → Adapters → CLI/Web separation         │
│  ├── Platform adapters: Windows/Linux/macOS scaffolding         │
│  ├── CLI: Typer-based with server/web/platform commands         │
│  ├── Database: SQLAlchemy 2.0 with Server model                 │
│  ├── API: FastAPI with REST endpoints                           │
│  ├── Frontend: React + Vite + Tailwind skeleton                 │
│  └── Tooling: Poetry, pre-commit, mypy, ruff, black             │
│                                                                  │
│  ⚠️  PLACEHOLDER (Must Implement)                                │
│  ├── installers.py - Returns True without downloading           │
│  ├── backups.py - Empty placeholder                             │
│  ├── plugins.py - Empty placeholder                             │
│  ├── scheduler.py - Empty placeholder                           │
│  ├── ws_console.py - Not connected to anything                  │
│  └── Platform services (systemd/launchd/Windows services)       │
│                                                                  │
│  🔴 CRITICAL BUGS                                                │
│  ├── DB sessions not properly managed (detached objects)        │
│  ├── Circular import risk (platform_adapters ↔ msm_core)        │
│  ├── Global state initialized at import time                    │
│  ├── Process state not synced on restart                        │
│  └── Empty env dict replaces system environment                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├──────────────────────┬──────────────────────┬───────────────────┤
│      CLI (msh)       │    Web Dashboard     │   REST API        │
│   Typer + Rich       │    React + Vite      │   FastAPI         │
│   ┌────────────┐     │   ┌────────────┐     │  ┌────────────┐   │
│   │ msh server │     │   │ Dashboard  │     │  │ /api/v1/*  │   │
│   │ msh web    │     │   │ Console    │     │  │ WebSocket  │   │
│   │ msh backup │     │   │ Settings   │     │  │ OpenAPI    │   │
│   └────────────┘     │   └────────────┘     │  └────────────┘   │
└──────────┬───────────┴──────────┬───────────┴─────────┬─────────┘
           │                      │                     │
           └──────────────────────┼─────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MSM CORE                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Lifecycle  │  │  Installer  │  │   Backup    │              │
│  │             │  │             │  │             │              │
│  │ start()    │  │ paper()     │  │ create()    │              │
│  │ stop()      │  │ fabric()    │  │ restore()   │              │
│  │ restart()   │  │ vanilla()   │  │ schedule()  │              │
│  │ status()    │  │ forge()     │  │ prune()     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Monitor   │  │   Plugin    │  │  Scheduler  │              │
│  │             │  │             │  │             │              │
│  │ cpu/ram     │  │ modrinth()  │  │ cron jobs   │              │
│  │ console     │  │ hangar()    │  │ auto-backup │              │
│  │ players     │  │ install()   │  │ auto-restart│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │                     Database                      │           │
│  │              SQLite + SQLAlchemy 2.0              │           │
│  │  Server │ Backup │ Schedule │ Plugin │ User       │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PLATFORM ADAPTERS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│   │   Windows   │   │    Linux    │   │    macOS    │           │
│   ├─────────────┤   ├─────────────┤   ├─────────────┤           │
│   │ AppData     │   │ XDG paths   │   │ ~/Library   │           │
│   │ PowerShell  │   │ systemd     │   │ launchd     │           │
│   │ netsh       │   │ ufw/firewalld│  │ pfctl       │           │
│   │ NSSM/sc.exe │   │ POSIX signals│  │ POSIX       │           │
│   │ winget      │   │ apt/dnf     │   │ brew        │           │
│   └─────────────┘   └─────────────┘   └─────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                           │
├─────────────────────────────────────────────────────────────────┤
│  PaperMC API │ Modrinth API │ Fabric Meta │ Mojang API          │
│  Adoptium    │ Hangar       │ CurseForge  │ (Java downloads)    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```sql
-- Core Tables
CREATE TABLE servers (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,              -- paper, fabric, vanilla, forge
    version TEXT NOT NULL,           -- 1.20.4, 1.21, etc.
    path TEXT NOT NULL,
    port INTEGER DEFAULT 25565,
    memory TEXT DEFAULT '2G',
    java_path TEXT,
    jvm_args TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    -- Runtime state (reconciled on startup)
    is_running BOOLEAN DEFAULT FALSE,
    pid INTEGER,
    last_started DATETIME,
    last_stopped DATETIME
);

CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    path TEXT NOT NULL,
    size_bytes INTEGER,
    created_at DATETIME,
    type TEXT DEFAULT 'manual',      -- manual, scheduled, pre-update
    status TEXT DEFAULT 'completed'  -- in_progress, completed, failed
);

CREATE TABLE schedules (
    id INTEGER PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    action TEXT NOT NULL,            -- backup, restart, stop, start, command
    cron TEXT NOT NULL,              -- "0 4 * * *" = 4am daily
    enabled BOOLEAN DEFAULT TRUE,
    last_run DATETIME,
    next_run DATETIME,
    payload TEXT                     -- JSON for additional args
);

CREATE TABLE plugins (
    id INTEGER PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    name TEXT NOT NULL,
    source TEXT,                     -- modrinth, hangar, manual
    source_id TEXT,                  -- modrinth project ID
    version TEXT,
    file_path TEXT,
    installed_at DATETIME,
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE console_history (
    id INTEGER PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    timestamp DATETIME,
    line TEXT,
    type TEXT                        -- stdout, stderr, stdin
);
```

---

# Part 5: Implementation Roadmap

## Phase 0: Foundation Fixes (Week 1)

**Goal:** Fix critical bugs before building more features.

| Task | Priority | Est |
|------|----------|-----|
| Fix DB session management (context managers) | P0 | 2h |
| Fix circular import (extract get_os_name) | P0 | 1h |
| Lazy init for GLOBAL_DB, GLOBAL_CONFIG | P0 | 2h |
| Process state reconciliation on startup | P0 | 2h |
| Fix empty env dict in start_process | P0 | 30m |
| Add proper exception hierarchy | P1 | 2h |
| Replace print() with logging | P1 | 2h |
| Add input validation (server names) | P1 | 1h |
| Add adapter singleton pattern | P2 | 1h |

**TOTAL: ~14h**

## Phase 1: Core Features (Weeks 2-3)

**Goal:** Achieve basic feature parity with Fork.

### 1.1 Server Installation (Actual Downloads)

```python
# msm_core/installers/paper.py
PAPER_API = "https://api.papermc.io/v2"

async def install_paper(version: str, dest: Path) -> bool:
    # 1. Get latest build for version
    builds = await fetch(f"{PAPER_API}/projects/paper/versions/{version}/builds")
    latest = builds["builds"][-1]

    # 2. Download JAR with SHA256 verification
    download_url = f"{PAPER_API}/projects/paper/versions/{version}/builds/{latest['build']}/downloads/{latest['downloads']['application']['name']}"
    sha256 = latest["downloads"]["application"]["sha256"]

    return await download_file(download_url, dest / "server.jar", sha256)
```

**Supported Server Types:**

| Type | API | Priority |
|------|-----|----------|
| Paper | api.papermc.io | P0 |
| Vanilla | launchermeta.mojang.com | P0 |
| Fabric | meta.fabricmc.net | P1 |
| Forge | files.minecraftforge.net | P2 |
| Purpur | api.purpurmc.org | P2 |

### 1.2 Console Streaming

```python
# web/backend/console.py
from fastapi import WebSocket
import asyncio

class ConsoleManager:
    def __init__(self):
        self.processes: Dict[int, asyncio.subprocess.Process] = {}
        self.connections: Dict[int, List[WebSocket]] = {}

    async def stream_console(self, server_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(server_id, []).append(websocket)

        try:
            while True:
                # Receive commands from client
                data = await websocket.receive_text()
                if data:
                    await self.send_command(server_id, data)
        except WebSocketDisconnect:
            self.connections[server_id].remove(websocket)

    async def broadcast_line(self, server_id: int, line: str):
        for ws in self.connections.get(server_id, []):
            await ws.send_text(line)
```

### 1.3 Backup System

```python
# msm_core/backups.py
import shutil
import tarfile
from datetime import datetime

def create_backup(server_id: int, output_dir: Optional[Path] = None) -> Path:
    server = get_server_by_id(server_id)

    # Stop server if running (optional, configurable)
    was_running = server.is_running
    if was_running:
        stop_server(server_id)

    # Create tarball
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{server.name}_{timestamp}.tar.gz"
    backup_path = (output_dir or get_backup_dir()) / backup_name

    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(server.path, arcname=server.name)

    # Restart if was running
    if was_running:
        start_server(server_id)

    # Record in database
    record_backup(server_id, backup_path)

    return backup_path
```

### 1.4 Server Deletion & Import

```python
# CLI commands
@server_app.command("delete")
def delete_server(name: str, keep_files: bool = False):
    """Delete a server."""
    server = api.get_server(name)
    if not server:
        raise typer.Exit(1)

    if server.is_running:
        typer.echo("Stop the server first.")
        raise typer.Exit(1)

    if not keep_files:
        shutil.rmtree(server.path)
    api.delete_server(server.id)
    typer.echo(f"Server '{name}' deleted.")

@server_app.command("import")
def import_server(
    path: Path,
    name: str,
    type: str = "paper",
    version: str = "1.20.4"
):
    """Import an existing server."""
    if not (path / "server.jar").exists():
        typer.echo("No server.jar found in directory.")
        raise typer.Exit(1)

    api.import_server(name, type, version, path)
    typer.echo(f"Server '{name}' imported.")
```

## Phase 2: User Experience (Weeks 4-5)

### 2.1 Java Management

```python
# platform_adapters/java.py
ADOPTIUM_API = "https://api.adoptium.net/v3"

class JavaManager:
    def detect_java(self) -> List[JavaInstallation]:
        """Find all Java installations on the system."""
        installations = []

        # Check PATH
        java_path = shutil.which("java")
        if java_path:
            installations.append(self.get_java_info(java_path))

        # Check common locations (platform-specific)
        for path in self.adapter.get_java_search_paths():
            if path.exists():
                installations.append(self.get_java_info(path))

        return installations

    def get_java_info(self, path: Path) -> JavaInstallation:
        """Get version info for a Java installation."""
        result = subprocess.run(
            [str(path), "-version"],
            capture_output=True,
            text=True
        )
        # Parse version from stderr (java -version outputs there)
        version = self.parse_version(result.stderr)
        return JavaInstallation(path=path, version=version)

    async def install_java(self, version: int = 21) -> Path:
        """Download and install Java from Adoptium."""
        # Determine OS and arch
        os_name = self.adapter.get_os_name()
        arch = platform.machine()

        # Fetch from Adoptium API
        url = f"{ADOPTIUM_API}/binary/latest/{version}/ga/{os_name}/{arch}/jdk/hotspot/normal/eclipse"
        # Download and extract...
```

### 2.2 Config Editor

```python
# msm_core/config_editor.py
import re
from pathlib import Path

class ServerPropertiesEditor:
    def __init__(self, server_path: Path):
        self.path = server_path / "server.properties"
        self.properties = self.load()

    def load(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}

        props = {}
        for line in self.path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
        return props

    def save(self):
        lines = [f"{k}={v}" for k, v in self.properties.items()]
        self.path.write_text("\n".join(lines))

    def get(self, key: str) -> Optional[str]:
        return self.properties.get(key)

    def set(self, key: str, value: str):
        self.properties[key] = value

# API endpoint
@app.get("/api/v1/servers/{server_id}/properties")
def get_properties(server_id: int):
    server = get_server_by_id(server_id)
    editor = ServerPropertiesEditor(Path(server.path))
    return editor.properties

@app.patch("/api/v1/servers/{server_id}/properties")
def update_properties(server_id: int, updates: Dict[str, str]):
    server = get_server_by_id(server_id)
    editor = ServerPropertiesEditor(Path(server.path))
    for key, value in updates.items():
        editor.set(key, value)
    editor.save()
    return {"status": "updated"}
```

### 2.3 Frontend Enhancements

```
web/frontend/src/
├── components/
│   ├── ServerCard.tsx        # Server list item
│   ├── ServerConsole.tsx     # WebSocket console viewer
│   ├── CreateServerModal.tsx # Server creation form
│   ├── PropertiesEditor.tsx  # server.properties editor
│   ├── StatsWidget.tsx       # CPU/RAM gauges
│   └── BackupList.tsx        # Backup management
├── pages/
│   ├── Dashboard.tsx         # Server overview
│   ├── ServerDetail.tsx      # Single server view
│   ├── Console.tsx           # Full-page console
│   └── Settings.tsx          # App settings
├── hooks/
│   ├── useServers.ts         # SWR for server list
│   ├── useWebSocket.ts       # Console WebSocket
│   └── useStats.ts           # System stats polling
└── lib/
    └── api.ts                # API client
```

## Phase 3: Power Features (Weeks 6-8)

### 3.1 Plugin Manager

```python
# msm_core/plugins/modrinth.py
MODRINTH_API = "https://api.modrinth.com/v2"

async def search_plugins(query: str, mc_version: str, loader: str = "paper"):
    params = {
        "query": query,
        "facets": f'[["versions:{mc_version}"],["categories:{loader}"]]',
        "limit": 20
    }
    response = await httpx.get(f"{MODRINTH_API}/search", params=params)
    return response.json()["hits"]

async def install_plugin(server_id: int, project_id: str):
    server = get_server_by_id(server_id)

    # Get latest compatible version
    versions = await get_project_versions(project_id, server.version)
    latest = versions[0]

    # Download to plugins folder
    plugins_dir = Path(server.path) / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    file_info = latest["files"][0]
    dest = plugins_dir / file_info["filename"]

    await download_file(file_info["url"], dest, file_info["hashes"]["sha512"])

    # Record in database
    record_plugin(server_id, project_id, latest["version_number"], dest)
```

### 3.2 Scheduler

```python
# msm_core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def schedule_backup(server_id: int, cron: str):
    """Schedule automatic backups."""
    trigger = CronTrigger.from_crontab(cron)
    scheduler.add_job(
        create_backup,
        trigger=trigger,
        args=[server_id],
        id=f"backup_{server_id}",
        replace_existing=True
    )

def schedule_restart(server_id: int, cron: str):
    """Schedule automatic restarts."""
    trigger = CronTrigger.from_crontab(cron)
    scheduler.add_job(
        restart_server,
        trigger=trigger,
        args=[server_id],
        id=f"restart_{server_id}",
        replace_existing=True
    )

# CLI
@server_app.command("schedule")
def schedule_cmd(
    name: str,
    action: str = typer.Argument(..., help="backup|restart|stop|start"),
    cron: str = typer.Argument(..., help="Cron expression, e.g. '0 4 * * *'")
):
    """Schedule automated actions."""
    server = api.get_server(name)
    if action == "backup":
        schedule_backup(server.id, cron)
    elif action == "restart":
        schedule_restart(server.id, cron)
    typer.echo(f"Scheduled {action} for '{name}': {cron}")
```

### 3.3 Discord Bot (Optional Module)

```python
# msm_discord/bot.py
import discord
from discord.ext import commands

class MSMBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def servers(self, ctx):
        """List all servers."""
        servers = api.list_servers()
        embed = discord.Embed(title="Minecraft Servers")
        for s in servers:
            status = "🟢 Running" if s.is_running else "🔴 Stopped"
            embed.add_field(name=s.name, value=f"{status}\n{s.version}")
        await ctx.send(embed=embed)

    @commands.command()
    async def start(self, ctx, name: str):
        """Start a server."""
        server = api.get_server(name)
        if lifecycle.start_server(server.id):
            await ctx.send(f"✅ Started {name}")
        else:
            await ctx.send(f"❌ Failed to start {name}")

    @commands.command()
    async def stop(self, ctx, name: str):
        """Stop a server."""
        server = api.get_server(name)
        if lifecycle.stop_server(server.id):
            await ctx.send(f"✅ Stopped {name}")
        else:
            await ctx.send(f"❌ Failed to stop {name}")
```

## Phase 4: Production Hardening (Weeks 9-10)

### 4.1 Authentication

```python
# web/backend/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import secrets

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Check against stored keys
    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key

# Protected endpoints
@app.post("/api/v1/servers/{server_id}/start", dependencies=[Depends(verify_api_key)])
def start_server(server_id: int):
    ...
```

### 4.2 System Services

```python
# platform_adapters/linux_adapter.py
SYSTEMD_TEMPLATE = """
[Unit]
Description=Minecraft Server - {name}
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={path}
ExecStart={java_path} -Xmx{memory} -jar server.jar nogui
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

def create_background_service(self, name: str, server: Server) -> bool:
    unit_content = SYSTEMD_TEMPLATE.format(
        name=server.name,
        user=os.getlogin(),
        path=server.path,
        java_path=self.get_java_path(),
        memory=server.memory
    )

    unit_path = Path(f"/etc/systemd/system/msm-{name}.service")
    unit_path.write_text(unit_content)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", f"msm-{name}"], check=True)
    return True
```

### 4.3 Comprehensive Test Suite

```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_data_dir(tmp_path):
    """Isolated data directory for each test."""
    return tmp_path / "msm_test"

@pytest.fixture
def db_session(temp_data_dir):
    """Fresh database for each test."""
    from msm_core.db import create_db_manager
    db = create_db_manager(temp_data_dir / "test.db")
    yield db.get_session()
    db.close()

@pytest.fixture
def mock_server(db_session, temp_data_dir):
    """Create a mock server for testing."""
    server_dir = temp_data_dir / "servers" / "test-server"
    server_dir.mkdir(parents=True)
    (server_dir / "server.jar").touch()
    (server_dir / "eula.txt").write_text("eula=true")

    from msm_core.db import Server
    server = Server(
        name="test-server",
        type="paper",
        version="1.20.4",
        path=str(server_dir),
        port=25565,
        memory="1G"
    )
    db_session.add(server)
    db_session.commit()

    return server

# tests/unit/test_lifecycle.py
def test_start_server_success(mock_server, mocker):
    mocker.patch("platform_adapters.get_adapter")
    # ...

def test_start_nonexistent_server(db_session):
    result = start_server(99999)
    assert result is False

def test_stop_already_stopped_server(mock_server):
    result = stop_server(mock_server.id)
    assert result is False
```

---

# Part 6: Unique Selling Propositions (USPs)

## Top 10 USPs for MSM

### Tier 1: Primary Differentiators

#### 1. "One Command, Any Platform"
```bash
pip install msm && msh server create --name survival --type paper
```

**Why it matters:** Pterodactyl needs Docker + PHP + MySQL + Wings. MCSManager needs Node.js + distributed setup. MSM: one pip install.

**Tagline:** *"From zero to Minecraft server in 60 seconds"*

#### 2. "CLI-First, GUI-Ready"
```bash
# Automate with shell scripts
msh server create --name "server-$DATE" --type paper
msh server start survival
msh backup create survival --output /backups/

# Or use the web dashboard
msh web start
```

**Why it matters:** Fork/Crafty are GUI-only. Pterodactyl CLI is limited. MSM gives full power to both camps.

**Tagline:** *"Script it or click it—your choice"*

#### 3. "True Cross-Platform, Native Feel"
```
Windows → Uses AppData, PowerShell, Windows services
Linux   → Uses XDG paths, systemd, POSIX signals
macOS   → Uses ~/Library, launchd
```

**Why it matters:** Fork is Windows-only. Others use Docker abstraction. MSM has native platform adapters.

**Tagline:** *"Native on every OS, not just running on it"*

### Tier 2: Strong Differentiators

#### 4. "SSH-Friendly Headless Operation"
```bash
ssh user@vps "msh server start survival"
ssh user@vps "msh backup create --all"
```

**Why it matters:** No GUI needed. Perfect for $5 VPS, Raspberry Pi, or any headless server.

**Tagline:** *"Runs where Docker can't, works where GUIs don't"*

#### 5. "Zero Dependencies, Zero Docker"
```
Pterodactyl: PHP + MySQL + Redis + Nginx + Docker + Wings
MCSManager:  Node.js + Distributed daemon architecture
Crafty:      Python + SQLite + complex setup
MSM:         Python. That's it.
```

**Why it matters:** Simpler = fewer failure points, easier debugging, lower resource usage.

**Tagline:** *"No Docker. No database server. No drama."*

#### 6. "Developer-First API"
```bash
# Auto-generated OpenAPI docs
curl http://localhost:5000/docs

# Clean REST endpoints
curl -X POST http://localhost:5000/api/v1/servers/1/start
```

**Why it matters:** Build custom dashboards, Discord bots, mobile apps on top of MSM.

**Tagline:** *"Your panel, your rules—build on our API"*

### Tier 3: Tactical Differentiators

#### 7. "Automation-Native"
```yaml
# GitHub Actions / CI/CD
- run: pip install msm
- run: msh server create --name test-server --type paper
- run: msh server start test-server
- run: ./run-tests.sh
- run: msh server stop test-server
```

**Why it matters:** Test Minecraft plugins in CI/CD pipelines. No other tool enables this easily.

**Tagline:** *"CI/CD for Minecraft—yes, really"*

#### 8. "Lightweight Resource Footprint"
```
MSM idle:        ~30MB RAM
Pterodactyl:     ~500MB+ (PHP + MySQL + Docker)
MCSManager:      ~150MB+ (Node.js + daemons)
```

**Why it matters:** Run on Raspberry Pi, cheap VPS, or alongside other services.

**Tagline:** *"Light enough for a Pi, powerful enough for production"*

#### 9. "Python Ecosystem Integration"
```python
# Extend with Python - no new language to learn
from msm_core import api

# Custom automation
for server in api.list_servers():
    if server.name.startswith("temp-"):
        api.delete_server(server.id)
```

**Why it matters:** Python is the #1 language. Huge talent pool. Easy extensions.

**Tagline:** *"Extend with Python, the language you already know"*

#### 10. "Modern Stack, No Legacy Baggage"
```
FastAPI        → Async, auto-docs, type-safe
Typer          → Beautiful CLI with --help for free
Pydantic       → Validated configs, no silent failures
SQLAlchemy 2.0 → Modern ORM patterns
React + Vite   → Fast frontend builds
```

**Why it matters:** Built on 2024 best practices, not legacy code from 2015.

**Tagline:** *"Built yesterday, for tomorrow"*

---

# Part 7: Go-to-Market Strategy

## Launch Phases

### Phase 1: Developer Preview (Month 1)
```
Target: Early adopters, Linux sysadmins, developers
Channels:
├── GitHub release (v0.1.0-alpha)
├── Reddit: r/admincraft, r/minecraft, r/selfhosted
├── Hacker News: "Show HN: CLI-first Minecraft server manager"
└── Dev.to / Hashnode blog posts

Goals:
├── 100 GitHub stars
├── 50 actual users
├── 20 issues/feature requests
└── Validate core value proposition
```

### Phase 2: Community Building (Months 2-3)
```
Target: Power users, content creators
Channels:
├── Discord server launch
├── Documentation site (docs.msm.dev)
├── YouTube tutorial by Minecraft server YouTubers
├── Comparison blog posts (MSM vs Pterodactyl, etc.)
└── Plugin developer outreach

Goals:
├── 500 GitHub stars
├── 200 Discord members
├── 5 community contributors
└── Feature parity with Fork
```

### Phase 3: Mainstream Push (Months 4-6)
```
Target: General Minecraft community
Channels:
├── ProductHunt launch
├── Minecraft forum posts
├── Spigot/Paper community posts
├── Conference talks (if applicable)
└── Integration with popular tools

Goals:
├── 2000 GitHub stars
├── 1000 Discord members
├── v1.0.0 stable release
└── 50+ contributors
```

## Messaging by Channel

### GitHub README (Hero Section)
```markdown
# MSM - Minecraft Server Manager

**One command. Any platform. Full control.**

pip install msm
msh server create --name survival --type paper --version 1.21
msh server start survival

The simple, cross-platform Minecraft server manager with CLI power and web convenience.

[Get Started](#installation) | [Documentation](https://docs.msm.dev) | [Discord](https://discord.msm.dev)
```

### Reddit Post
```
Title: I built a CLI-first Minecraft server manager that works on Linux, Mac, and Windows

Hey r/admincraft,

I was frustrated that every Minecraft server manager either:
- Only works on Windows (Fork)
- Requires Docker + PHP + MySQL (Pterodactyl)
- Has no CLI for automation

So I built MSM. One pip install, works everywhere, scriptable.

Features:
- Create/start/stop servers from terminal
- Web dashboard included
- 30MB RAM footprint
- Works over SSH on headless servers
- REST API for custom tooling

It's free and open source. Looking for feedback!

GitHub: [link]
```

### Hacker News
```
Title: Show HN: MSM – A CLI-first, cross-platform Minecraft server manager

I built MSM because existing solutions are either Windows-only
or require enterprise-grade infrastructure just to host a
game server for friends.

Key decisions:
- Python for accessibility
- CLI-first, GUI-second
- Platform-native (no Docker requirement)
- <50MB memory footprint

The codebase is clean and extensible. Would love feedback
from the HN community, especially on the API design.
```

---

# Part 8: Success Metrics

## North Star Metric
**Weekly Active Servers Managed**

(Users who run `msh server start` at least once per week)

## Supporting Metrics

| Metric | Month 1 | Month 3 | Month 6 | Year 1 |
|--------|---------|---------|---------|--------|
| GitHub Stars | 100 | 500 | 2,000 | 5,000 |
| PyPI Downloads/month | 50 | 500 | 2,000 | 10,000 |
| Discord Members | - | 200 | 1,000 | 3,000 |
| Contributors | 1 | 5 | 15 | 30 |
| Servers Managed* | 20 | 200 | 1,000 | 5,000 |

*Opt-in telemetry

## Competitive Benchmarks

| Competitor | GitHub Stars | Our Target (Year 1) |
|------------|--------------|---------------------|
| Pterodactyl | 7,000+ | Not competing directly |
| MCSManager | 3,000+ | Match |
| Crafty | 1,500+ | Exceed |
| Fork | 500+ | Exceed |

---

# Part 9: Risk Assessment

## Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Minecraft API changes | Medium | High | Abstract installers, quick updates |
| Python version issues | Low | Medium | Support 3.11+, test matrix |
| Platform-specific bugs | High | Medium | CI testing on all 3 platforms |
| Performance at scale | Low | Medium | Benchmark with 20+ servers |

## Market Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Pterodactyl adds CLI | Low | High | Move faster, own the niche |
| Fork goes cross-platform | Medium | High | Differentiate on CLI/API |
| New competitor emerges | Medium | Medium | Build community moat |
| Minecraft popularity decline | Low | High | Support other games (future) |

## Execution Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Solo developer burnout | High | Critical | Build community early |
| Scope creep | High | Medium | Strict phase discipline |
| Poor documentation | Medium | High | Doc-as-code, examples-first |

---

# Part 10: The Winning Formula

## Why MSM Will Win

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE MSM ADVANTAGE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. RIGHT COMPLEXITY                                             │
│     ├── Simpler than: Pterodactyl, MCSManager                   │
│     ├── More powerful than: Fork, manual scripts                │
│     └── Sweet spot for 80% of users                              │
│                                                                  │
│  2. RIGHT PLATFORM                                               │
│     ├── Only true cross-platform option                          │
│     ├── Linux server market is underserved                       │
│     └── Mac users have zero good options                         │
│                                                                  │
│  3. RIGHT INTERFACE                                              │
│     ├── CLI-first = scriptable, automatable, SSH-friendly        │
│     ├── Web dashboard = accessible to everyone                   │
│     └── API-first = developers can build on top                  │
│                                                                  │
│  4. RIGHT TECHNOLOGY                                             │
│     ├── Python = largest developer community                     │
│     ├── Modern stack = attracts contributors                     │
│     └── Clean architecture = maintainable long-term              │
│                                                                  │
│  5. RIGHT TIMING                                                 │
│     ├── Fork v2 stalled for years                                │
│     ├── Pterodactyl too complex for most                         │
│     ├── Cloud gaming pushing self-hosting interest               │
│     └── DevOps practices reaching gaming communities             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## The Unfair Advantage

**Network Effects:**
- More users → More contributors → More features → More users
- Plugin ecosystem → Lock-in → Platform gravity

**Switching Costs:**
- Server configs stored in MSM format
- Backup formats standardized to MSM
- Automation scripts built on `msh`

**Community Moat:**
- Discord community
- Plugin developers
- Content creators
- Documentation contributors

---

# Part 11: Immediate Next Actions

## This Week

```bash
# Priority order - do these first

□ 1. Fix DB session management (context managers)
     File: msm_core/db.py

□ 2. Implement Paper download in installers.py
     File: msm_core/installers.py
     API: https://api.papermc.io/v2

□ 3. Connect WebSocket console to process stdout
     Files: web/backend/ws_console.py, web/backend/app.py

□ 4. Add server delete command
     File: cli/main.py

□ 5. Fix circular import
     Move get_os_name() to standalone module
```

## This Month

```
Week 1: Foundation fixes + Paper installer
Week 2: Console streaming + Vanilla installer
Week 3: Backup system + Server import
Week 4: Frontend create form + Console viewer
```

## Before First Public Release

```
□ All critical bugs fixed
□ Paper + Vanilla installers working
□ Console streaming functional
□ Backup/restore working
□ Server CRUD complete (create, read, update, delete, import)
□ Basic frontend with all features
□ README with GIFs/screenshots
□ Basic documentation
□ Tested on Windows, Linux, macOS
□ GitHub Actions CI passing
```

---

# Final Words

This project has the right foundation. The architecture is clean, the technology choices are modern, and the market opportunity is real.

The path to winning:
1. **Execute Phase 0-1 flawlessly** — Fix bugs, implement core features
2. **Ship early, ship often** — Get it in users' hands
3. **Listen obsessively** — Let the community guide priorities
4. **Stay focused** — CLI + Web + API, nothing else until v1.0
5. **Build in public** — Share progress, attract contributors

The Minecraft server management space is waiting for a tool that "just works" on any platform. Be that tool.

**Now go build it.** 🚀
