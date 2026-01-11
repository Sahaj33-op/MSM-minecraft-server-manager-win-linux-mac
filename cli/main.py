"""MSM CLI - Minecraft Server Manager Command Line Interface."""
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

from msm_core import api
from msm_core.lifecycle import start_server, stop_server, restart_server, sync_server_states, get_server_status
from msm_core.exceptions import MSMError, ServerNotFoundError, ValidationError
from msm_core.installers import get_available_versions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("msm")

# Rich console for pretty output
console = Console()

# CLI app
app = typer.Typer(
    name="msh",
    help="MSM - Minecraft Server Manager CLI",
    no_args_is_help=True,
)

# Sub-commands
server_app = typer.Typer(help="Server management commands")
app.add_typer(server_app, name="server")

web_app = typer.Typer(help="Web dashboard commands")
app.add_typer(web_app, name="web")

config_app = typer.Typer(help="Configuration commands")
app.add_typer(config_app, name="config")

backup_app = typer.Typer(help="Backup management commands")
app.add_typer(backup_app, name="backup")

plugin_app = typer.Typer(help="Plugin management commands")
app.add_typer(plugin_app, name="plugin")

schedule_app = typer.Typer(help="Schedule management commands")
app.add_typer(schedule_app, name="schedule")

java_app = typer.Typer(help="Java runtime management commands")
app.add_typer(java_app, name="java")


def handle_error(e: Exception) -> None:
    """Handle and display errors nicely."""
    if isinstance(e, MSMError):
        console.print(f"[red]Error:[/red] {e}")
    else:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.exception("Unexpected error")
    raise typer.Exit(1)


# ============================================================================
# Server Commands
# ============================================================================

@server_app.command("create")
def create_server_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Server name"),
    server_type: str = typer.Option("paper", "--type", "-t", help="Server type (paper, vanilla, fabric, purpur)"),
    version: str = typer.Option("1.20.4", "--version", "-v", help="Minecraft version"),
    memory: str = typer.Option("2G", "--memory", "-m", help="Memory allocation (e.g., 2G, 4G)"),
    port: int = typer.Option(25565, "--port", "-p", help="Server port"),
):
    """Create a new Minecraft server."""
    try:
        with console.status(f"Creating {server_type} server '{name}'..."):
            server = api.create_server(name, server_type, version, memory, port)

        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' created successfully!")
        console.print(f"  Type: {server_type}")
        console.print(f"  Version: {version}")
        console.print(f"  Memory: {memory}")
        console.print(f"  Port: {port}")
        console.print(f"\nStart with: [cyan]msh server start {name}[/cyan]")

    except Exception as e:
        handle_error(e)


@server_app.command("delete")
def delete_server_cmd(
    name: str = typer.Argument(..., help="Server name"),
    keep_files: bool = typer.Option(False, "--keep-files", "-k", help="Keep server files on disk"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a server."""
    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        if server["is_running"]:
            console.print(f"[red]Error:[/red] Server '{name}' is running. Stop it first.")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete server '{name}'?")
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        api.delete_server(name, keep_files=keep_files)
        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' deleted.")
        if keep_files:
            console.print(f"  Files kept at: {server['path']}")

    except Exception as e:
        handle_error(e)


@server_app.command("start")
def start_server_cmd(name: str = typer.Argument(..., help="Server name")):
    """Start a server."""
    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status(f"Starting server '{name}'..."):
            start_server(server["id"])

        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' started.")

    except Exception as e:
        handle_error(e)


@server_app.command("stop")
def stop_server_cmd(name: str = typer.Argument(..., help="Server name")):
    """Stop a server."""
    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status(f"Stopping server '{name}'..."):
            stop_server(server["id"])

        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' stopped.")

    except Exception as e:
        handle_error(e)


@server_app.command("restart")
def restart_server_cmd(name: str = typer.Argument(..., help="Server name")):
    """Restart a server."""
    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status(f"Restarting server '{name}'..."):
            restart_server(server["id"])

        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' restarted.")

    except Exception as e:
        handle_error(e)


@server_app.command("list")
def list_servers_cmd():
    """List all servers."""
    try:
        # Sync server states first
        sync_server_states()

        servers = api.list_servers()

        if not servers:
            console.print("No servers found. Create one with: [cyan]msh server create --name my-server[/cyan]")
            return

        table = Table(title="Minecraft Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Version")
        table.add_column("Port")
        table.add_column("Memory")
        table.add_column("Status")

        for s in servers:
            status = "[green]Running[/green]" if s["is_running"] else "[dim]Stopped[/dim]"
            if s["is_running"] and s["pid"]:
                status = f"[green]Running[/green] (PID: {s['pid']})"

            table.add_row(
                s["name"],
                s["type"],
                s["version"],
                str(s["port"]),
                s["memory"],
                status,
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


@server_app.command("status")
def status_server_cmd(name: str = typer.Argument(..., help="Server name")):
    """Show detailed server status."""
    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        status = get_server_status(server["id"])

        console.print(f"\n[bold]Server: {name}[/bold]")
        console.print(f"  Type: {status['type']}")
        console.print(f"  Version: {status['version']}")
        console.print(f"  Port: {status['port']}")
        console.print(f"  Memory: {status['memory']}")

        if status["is_running"]:
            console.print(f"  Status: [green]Running[/green] (PID: {status['pid']})")
            if "process" in status:
                proc = status["process"]
                console.print(f"  CPU: {proc['cpu_percent']:.1f}%")
                console.print(f"  RAM: {proc['memory_rss'] / (1024*1024):.1f} MB")
                console.print(f"  Uptime: {proc['uptime']:.0f}s")
        else:
            console.print("  Status: [dim]Stopped[/dim]")

        if status.get("last_started"):
            console.print(f"  Last Started: {status['last_started']}")
        if status.get("last_stopped"):
            console.print(f"  Last Stopped: {status['last_stopped']}")

    except Exception as e:
        handle_error(e)


@server_app.command("import")
def import_server_cmd(
    path: Path = typer.Argument(..., help="Path to existing server directory"),
    name: str = typer.Option(..., "--name", "-n", help="Name for the imported server"),
    server_type: str = typer.Option("paper", "--type", "-t", help="Server type"),
    version: str = typer.Option("1.20.4", "--version", "-v", help="Minecraft version"),
    memory: str = typer.Option("2G", "--memory", "-m", help="Memory allocation"),
    port: int = typer.Option(25565, "--port", "-p", help="Server port"),
):
    """Import an existing server directory."""
    try:
        server = api.import_server(name, server_type, version, path, memory, port)
        console.print(f"[green]✓[/green] Server '[bold]{name}[/bold]' imported from {path}")

    except Exception as e:
        handle_error(e)


@server_app.command("versions")
def versions_cmd(
    server_type: str = typer.Argument("paper", help="Server type (paper, vanilla, fabric, purpur)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of versions to show"),
):
    """List available versions for a server type."""
    try:
        with console.status(f"Fetching {server_type} versions..."):
            versions = get_available_versions(server_type)

        if not versions:
            console.print(f"No versions found for {server_type}")
            return

        console.print(f"\n[bold]Available {server_type} versions:[/bold]")
        for v in versions[-limit:]:
            console.print(f"  • {v}")

        if len(versions) > limit:
            console.print(f"\n  ... and {len(versions) - limit} more")

    except Exception as e:
        handle_error(e)


@server_app.command("console")
def console_cmd(name: str = typer.Argument(..., help="Server name")):
    """Attach to a server's console (interactive mode).

    Type commands to send them to the server.
    Press Ctrl+C to detach.
    """
    from msm_core.console import get_console_manager
    from msm_core.lifecycle import send_command
    import threading
    import time

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        if not server["is_running"]:
            console.print(f"[red]Error:[/red] Server '{name}' is not running")
            raise typer.Exit(1)

        console.print(f"[green]Attached to server '{name}' console[/green]")
        console.print("[dim]Type commands to send them to the server. Press Ctrl+C to detach.[/dim]\n")

        # Get console manager and subscribe to output
        cm = get_console_manager()
        server_proc = cm.get_process(server["id"])

        if not server_proc:
            console.print("[yellow]Warning:[/yellow] Console not available (server may have been started externally)")
            raise typer.Exit(1)

        # Print existing history
        history = server_proc.buffer.get_history(50)
        for entry in history:
            _print_console_line(entry)

        # Subscribe to new output
        def on_output(entry: dict):
            _print_console_line(entry)

        server_proc.buffer.subscribe(on_output)

        try:
            # Read commands from stdin
            while True:
                try:
                    cmd = input()
                    if cmd.strip():
                        send_command(server["id"], cmd)
                except EOFError:
                    break
        finally:
            server_proc.buffer.unsubscribe(on_output)

        console.print("\n[dim]Detached from console[/dim]")

    except KeyboardInterrupt:
        console.print("\n[dim]Detached from console[/dim]")
    except Exception as e:
        handle_error(e)


@server_app.command("cmd")
def send_cmd(
    name: str = typer.Argument(..., help="Server name"),
    command: str = typer.Argument(..., help="Command to send"),
):
    """Send a command to a running server."""
    from msm_core.lifecycle import send_command as lifecycle_send_command

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        if not server["is_running"]:
            console.print(f"[red]Error:[/red] Server '{name}' is not running")
            raise typer.Exit(1)

        if lifecycle_send_command(server["id"], command):
            console.print(f"[green]✓[/green] Sent command: {command}")
        else:
            console.print(f"[red]Error:[/red] Failed to send command")
            raise typer.Exit(1)

    except Exception as e:
        handle_error(e)


def _print_console_line(entry: dict):
    """Print a console output line with formatting."""
    timestamp = entry.get("timestamp", "")[:19]  # Trim to seconds
    stream = entry.get("stream", "stdout")
    line = entry.get("line", "")

    if stream == "stderr":
        console.print(f"[dim]{timestamp}[/dim] [red]{line}[/red]")
    else:
        console.print(f"[dim]{timestamp}[/dim] {line}")


# ============================================================================
# Backup Commands
# ============================================================================

@backup_app.command("create")
def backup_create_cmd(
    name: str = typer.Argument(..., help="Server name"),
    stop_first: bool = typer.Option(False, "--stop", "-s", help="Stop server before backup"),
):
    """Create a backup of a server."""
    from msm_core.backups import create_backup

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status(f"Creating backup of '{name}'..."):
            result = create_backup(server["id"], stop_first=stop_first)

        size_mb = result["size_bytes"] / (1024 * 1024)
        console.print(f"[green]✓[/green] Backup created: [bold]{result['path']}[/bold]")
        console.print(f"  Size: {size_mb:.1f} MB")

    except Exception as e:
        handle_error(e)


@backup_app.command("list")
def backup_list_cmd(
    name: Optional[str] = typer.Argument(None, help="Server name (optional, lists all if not provided)"),
):
    """List backups for a server or all servers."""
    from msm_core.backups import list_backups

    try:
        server_id = None
        if name:
            server = api.get_server(name)
            if not server:
                raise ServerNotFoundError(name)
            server_id = server["id"]

        backups = list_backups(server_id)

        if not backups:
            console.print("No backups found.")
            return

        table = Table(title="Backups")
        table.add_column("ID", style="dim")
        table.add_column("Server", style="cyan")
        table.add_column("Type")
        table.add_column("Size")
        table.add_column("Created")
        table.add_column("Status")

        # Get server names for display
        servers = {s["id"]: s["name"] for s in api.list_servers()}

        for b in backups:
            size_mb = (b["size_bytes"] or 0) / (1024 * 1024)
            status = "[green]OK[/green]" if b["exists"] else "[red]Missing[/red]"
            created = b["created_at"][:19] if b["created_at"] else "Unknown"

            table.add_row(
                str(b["id"]),
                servers.get(b["server_id"], "Unknown"),
                b["type"],
                f"{size_mb:.1f} MB",
                created,
                status,
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


@backup_app.command("restore")
def backup_restore_cmd(
    backup_id: int = typer.Argument(..., help="Backup ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Restore a server from a backup."""
    from msm_core.backups import restore_backup, get_backup_by_id

    try:
        backup = get_backup_by_id(backup_id)
        if not backup:
            console.print(f"[red]Error:[/red] Backup {backup_id} not found")
            raise typer.Exit(1)

        if not backup["exists"]:
            console.print(f"[red]Error:[/red] Backup file not found at {backup['path']}")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(
                f"This will overwrite the server files. Continue?"
            )
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        with console.status("Restoring backup..."):
            restore_backup(backup_id)

        console.print(f"[green]✓[/green] Backup restored successfully!")

    except Exception as e:
        handle_error(e)


@backup_app.command("delete")
def backup_delete_cmd(
    backup_id: int = typer.Argument(..., help="Backup ID"),
    keep_file: bool = typer.Option(False, "--keep-file", "-k", help="Keep the backup file on disk"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a backup."""
    from msm_core.backups import delete_backup, get_backup_by_id

    try:
        backup = get_backup_by_id(backup_id)
        if not backup:
            console.print(f"[red]Error:[/red] Backup {backup_id} not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Delete backup {backup_id}?")
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        delete_backup(backup_id, delete_file=not keep_file)
        console.print(f"[green]✓[/green] Backup deleted.")

    except Exception as e:
        handle_error(e)


@backup_app.command("prune")
def backup_prune_cmd(
    name: Optional[str] = typer.Argument(None, help="Server name (optional, prunes all if not provided)"),
    keep: int = typer.Option(5, "--keep", "-k", help="Number of backups to keep"),
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Only delete backups older than N days"),
):
    """Prune old backups, keeping the most recent ones."""
    from msm_core.backups import prune_backups

    try:
        server_id = None
        if name:
            server = api.get_server(name)
            if not server:
                raise ServerNotFoundError(name)
            server_id = server["id"]

        deleted = prune_backups(server_id, keep_count=keep, keep_days=days)
        console.print(f"[green]✓[/green] Pruned {deleted} backup(s).")

    except Exception as e:
        handle_error(e)


# ============================================================================
# Plugin Commands
# ============================================================================

@plugin_app.command("search")
def plugin_search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option("modrinth", "--source", "-s", help="Source (modrinth, hangar)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
):
    """Search for plugins on Modrinth or Hangar."""
    from msm_core.plugins import search_modrinth, search_hangar

    try:
        with console.status(f"Searching {source}..."):
            if source == "modrinth":
                results = search_modrinth(query, limit=limit)
            elif source == "hangar":
                results = search_hangar(query, limit=limit)
            else:
                console.print(f"[red]Error:[/red] Unknown source '{source}'. Use 'modrinth' or 'hangar'.")
                raise typer.Exit(1)

        if not results:
            console.print("No plugins found.")
            return

        table = Table(title=f"Plugins from {source.capitalize()}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Author")
        table.add_column("Downloads")
        table.add_column("Description", max_width=40)

        for p in results:
            table.add_row(
                p["slug"],
                p["name"],
                p["author"],
                f"{p['downloads']:,}",
                (p["description"][:37] + "...") if len(p["description"]) > 40 else p["description"],
            )

        console.print(table)
        console.print(f"\nInstall with: [cyan]msh plugin install <server> {source}:<id>[/cyan]")

    except Exception as e:
        handle_error(e)


@plugin_app.command("install")
def plugin_install_cmd(
    name: str = typer.Argument(..., help="Server name"),
    plugin: str = typer.Argument(..., help="Plugin identifier (modrinth:<id>, hangar:<id>, or URL)"),
):
    """Install a plugin from Modrinth, Hangar, or URL."""
    from msm_core.plugins import install_from_modrinth, install_from_url

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status(f"Installing plugin..."):
            if plugin.startswith("modrinth:"):
                project_id = plugin[9:]
                result = install_from_modrinth(server["id"], project_id, mc_version=server["version"])
            elif plugin.startswith("hangar:"):
                # For Hangar, we'd need to implement install_from_hangar
                console.print("[yellow]Hangar installation not yet implemented. Use direct URL.[/yellow]")
                raise typer.Exit(1)
            elif plugin.startswith("http://") or plugin.startswith("https://"):
                result = install_from_url(server["id"], plugin)
            else:
                # Assume Modrinth if no prefix
                result = install_from_modrinth(server["id"], plugin, mc_version=server["version"])

        console.print(f"[green]✓[/green] Installed [bold]{result['name']}[/bold]")
        console.print(f"  File: {result['file_name']}")
        if result.get("version"):
            console.print(f"  Version: {result['version']}")

    except Exception as e:
        handle_error(e)


@plugin_app.command("list")
def plugin_list_cmd(name: str = typer.Argument(..., help="Server name")):
    """List installed plugins for a server."""
    from msm_core.plugins import list_plugins

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        plugins = list_plugins(server["id"])

        if not plugins:
            console.print(f"No plugins installed on '{name}'.")
            return

        table = Table(title=f"Plugins for {name}")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Source")
        table.add_column("Status")

        for p in plugins:
            status = "[green]Enabled[/green]" if p["enabled"] else "[dim]Disabled[/dim]"
            if not p["exists"]:
                status = "[red]Missing[/red]"

            table.add_row(
                str(p["id"]),
                p["name"],
                p["version"] or "-",
                p["source"] or "manual",
                status,
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


@plugin_app.command("uninstall")
def plugin_uninstall_cmd(
    plugin_id: int = typer.Argument(..., help="Plugin ID"),
    keep_file: bool = typer.Option(False, "--keep-file", "-k", help="Keep the plugin file"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Uninstall a plugin."""
    from msm_core.plugins import uninstall_plugin, get_plugin_by_id

    try:
        plugin = get_plugin_by_id(plugin_id)
        if not plugin:
            console.print(f"[red]Error:[/red] Plugin {plugin_id} not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Uninstall plugin '{plugin['name']}'?")
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        uninstall_plugin(plugin_id, delete_file=not keep_file)
        console.print(f"[green]✓[/green] Plugin '{plugin['name']}' uninstalled.")

    except Exception as e:
        handle_error(e)


@plugin_app.command("enable")
def plugin_enable_cmd(plugin_id: int = typer.Argument(..., help="Plugin ID")):
    """Enable a disabled plugin."""
    from msm_core.plugins import toggle_plugin, get_plugin_by_id

    try:
        plugin = get_plugin_by_id(plugin_id)
        if not plugin:
            console.print(f"[red]Error:[/red] Plugin {plugin_id} not found")
            raise typer.Exit(1)

        if plugin["enabled"]:
            console.print(f"Plugin '{plugin['name']}' is already enabled.")
            return

        toggle_plugin(plugin_id, enabled=True)
        console.print(f"[green]✓[/green] Plugin '{plugin['name']}' enabled.")

    except Exception as e:
        handle_error(e)


@plugin_app.command("disable")
def plugin_disable_cmd(plugin_id: int = typer.Argument(..., help="Plugin ID")):
    """Disable a plugin (moves to disabled folder)."""
    from msm_core.plugins import toggle_plugin, get_plugin_by_id

    try:
        plugin = get_plugin_by_id(plugin_id)
        if not plugin:
            console.print(f"[red]Error:[/red] Plugin {plugin_id} not found")
            raise typer.Exit(1)

        if not plugin["enabled"]:
            console.print(f"Plugin '{plugin['name']}' is already disabled.")
            return

        toggle_plugin(plugin_id, enabled=False)
        console.print(f"[green]✓[/green] Plugin '{plugin['name']}' disabled.")

    except Exception as e:
        handle_error(e)


@plugin_app.command("updates")
def plugin_updates_cmd(name: str = typer.Argument(..., help="Server name")):
    """Check for plugin updates."""
    from msm_core.plugins import check_plugin_updates

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        with console.status("Checking for updates..."):
            updates = check_plugin_updates(server["id"])

        if not updates:
            console.print("[green]✓[/green] All plugins are up to date.")
            return

        table = Table(title="Available Updates")
        table.add_column("Plugin", style="cyan")
        table.add_column("Current")
        table.add_column("Latest", style="green")
        table.add_column("Source")

        for u in updates:
            table.add_row(
                u["name"],
                u["current_version"],
                u["latest_version"],
                u["source"],
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


# ============================================================================
# Schedule Commands
# ============================================================================

@schedule_app.command("create")
def schedule_create_cmd(
    name: str = typer.Argument(..., help="Server name"),
    action: str = typer.Option(..., "--action", "-a", help="Action (backup, restart, stop, start, command)"),
    cron: str = typer.Option(..., "--cron", "-c", help="Cron expression (e.g., '0 4 * * *' for 4am daily)"),
    command: Optional[str] = typer.Option(None, "--command", help="Command to run (for action=command)"),
):
    """Create a scheduled task for a server."""
    from msm_core.scheduler import create_schedule
    import json

    try:
        server = api.get_server(name)
        if not server:
            raise ServerNotFoundError(name)

        payload = None
        if action == "command" and command:
            payload = json.dumps({"command": command})

        result = create_schedule(
            server_id=server["id"],
            action=action,
            cron_expr=cron,
            payload=payload,
        )

        console.print(f"[green]✓[/green] Schedule created (ID: {result['id']})")
        console.print(f"  Action: {action}")
        console.print(f"  Cron: {cron}")
        if result["next_run"]:
            console.print(f"  Next run: {result['next_run']}")

    except Exception as e:
        handle_error(e)


@schedule_app.command("list")
def schedule_list_cmd(
    name: Optional[str] = typer.Argument(None, help="Server name (optional, lists all if not provided)"),
):
    """List scheduled tasks."""
    from msm_core.scheduler import list_schedules

    try:
        server_id = None
        if name:
            server = api.get_server(name)
            if not server:
                raise ServerNotFoundError(name)
            server_id = server["id"]

        schedules = list_schedules(server_id)

        if not schedules:
            console.print("No schedules found.")
            return

        table = Table(title="Scheduled Tasks")
        table.add_column("ID", style="dim")
        table.add_column("Server", style="cyan")
        table.add_column("Action")
        table.add_column("Cron")
        table.add_column("Status")
        table.add_column("Next Run")

        servers = {s["id"]: s["name"] for s in api.list_servers()}

        for s in schedules:
            status = "[green]Enabled[/green]" if s["enabled"] else "[dim]Disabled[/dim]"
            next_run = s["next_run"][:19] if s["next_run"] else "-"

            table.add_row(
                str(s["id"]),
                servers.get(s["server_id"], "Unknown"),
                s["action"],
                s["cron"],
                status,
                next_run,
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


@schedule_app.command("delete")
def schedule_delete_cmd(
    schedule_id: int = typer.Argument(..., help="Schedule ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a scheduled task."""
    from msm_core.scheduler import delete_schedule, get_schedule_by_id

    try:
        schedule = get_schedule_by_id(schedule_id)
        if not schedule:
            console.print(f"[red]Error:[/red] Schedule {schedule_id} not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Delete schedule {schedule_id}?")
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        delete_schedule(schedule_id)
        console.print(f"[green]✓[/green] Schedule deleted.")

    except Exception as e:
        handle_error(e)


@schedule_app.command("enable")
def schedule_enable_cmd(schedule_id: int = typer.Argument(..., help="Schedule ID")):
    """Enable a disabled schedule."""
    from msm_core.scheduler import update_schedule, get_schedule_by_id

    try:
        schedule = get_schedule_by_id(schedule_id)
        if not schedule:
            console.print(f"[red]Error:[/red] Schedule {schedule_id} not found")
            raise typer.Exit(1)

        if schedule["enabled"]:
            console.print("Schedule is already enabled.")
            return

        result = update_schedule(schedule_id, enabled=True)
        console.print(f"[green]✓[/green] Schedule enabled.")
        if result["next_run"]:
            console.print(f"  Next run: {result['next_run']}")

    except Exception as e:
        handle_error(e)


@schedule_app.command("disable")
def schedule_disable_cmd(schedule_id: int = typer.Argument(..., help="Schedule ID")):
    """Disable a schedule."""
    from msm_core.scheduler import update_schedule, get_schedule_by_id

    try:
        schedule = get_schedule_by_id(schedule_id)
        if not schedule:
            console.print(f"[red]Error:[/red] Schedule {schedule_id} not found")
            raise typer.Exit(1)

        if not schedule["enabled"]:
            console.print("Schedule is already disabled.")
            return

        update_schedule(schedule_id, enabled=False)
        console.print(f"[green]✓[/green] Schedule disabled.")

    except Exception as e:
        handle_error(e)


# ============================================================================
# Java Commands
# ============================================================================

@java_app.command("list")
def java_list_cmd(
    managed_only: bool = typer.Option(False, "--managed", "-m", help="Only show MSM-managed installations"),
):
    """List detected Java installations."""
    from msm_core.java_manager import detect_installed_javas, get_managed_javas

    try:
        if managed_only:
            javas = get_managed_javas()
            title = "MSM-Managed Java Installations"
        else:
            javas = detect_installed_javas()
            title = "Detected Java Installations"

        if not javas:
            if managed_only:
                console.print("No MSM-managed Java installations found.")
                console.print("Install with: [cyan]msh java install <version>[/cyan]")
            else:
                console.print("No Java installations detected.")
            return

        table = Table(title=title)
        table.add_column("Version", style="cyan")
        table.add_column("Major")
        table.add_column("Vendor")
        table.add_column("Path", max_width=50)

        for j in javas:
            table.add_row(
                j["version"],
                str(j["major_version"]),
                j["vendor"],
                j["path"],
            )

        console.print(table)

    except Exception as e:
        handle_error(e)


@java_app.command("detect")
def java_detect_cmd():
    """Detect best Java for different Minecraft versions."""
    from msm_core.java_manager import detect_installed_javas, get_best_java_for_version

    try:
        javas = detect_installed_javas()

        if not javas:
            console.print("[yellow]No Java installations detected.[/yellow]")
            console.print("Install Java with: [cyan]msh java install 21[/cyan]")
            return

        console.print("[bold]Java recommendations by Minecraft version:[/bold]\n")

        mc_versions = ["1.20.5", "1.20.4", "1.18.2", "1.16.5", "1.12.2"]

        for mc_ver in mc_versions:
            best = get_best_java_for_version(mc_ver, javas)
            if best:
                console.print(f"  MC {mc_ver}: Java {best['major_version']} ({best['vendor']})")
            else:
                console.print(f"  MC {mc_ver}: [red]No compatible Java found[/red]")

    except Exception as e:
        handle_error(e)


@java_app.command("available")
def java_available_cmd():
    """Show available Java versions for download."""
    from msm_core.java_manager import get_available_java_versions

    try:
        with console.status("Fetching available versions..."):
            versions = get_available_java_versions()

        if not versions:
            console.print("No versions available.")
            return

        console.print("[bold]Available Java versions from Eclipse Temurin:[/bold]\n")

        for v in versions:
            lts = " [green](LTS)[/green]" if v["lts"] else ""
            console.print(f"  • Java {v['version']}{lts}")

        console.print("\nInstall with: [cyan]msh java install <version>[/cyan]")

    except Exception as e:
        handle_error(e)


@java_app.command("install")
def java_install_cmd(
    version: int = typer.Argument(..., help="Java major version to install (e.g., 17, 21)"),
):
    """Download and install a Java runtime."""
    from msm_core.java_manager import download_java

    try:
        with console.status(f"Downloading Java {version}..."):
            result = download_java(version)

        console.print(f"[green]✓[/green] Java {result['version']} installed!")
        console.print(f"  Vendor: {result['vendor']}")
        console.print(f"  Path: {result['java_home']}")

    except Exception as e:
        handle_error(e)


@java_app.command("remove")
def java_remove_cmd(
    path: str = typer.Argument(..., help="Path to Java home directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove an MSM-managed Java installation."""
    from msm_core.java_manager import delete_managed_java

    try:
        if not force:
            confirm = typer.confirm(f"Remove Java installation at {path}?")
            if not confirm:
                console.print("Cancelled.")
                raise typer.Exit(0)

        delete_managed_java(path)
        console.print(f"[green]✓[/green] Java installation removed.")

    except Exception as e:
        handle_error(e)


# ============================================================================
# Web Commands
# ============================================================================

@web_app.command("start")
def start_web_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(5000, "--port", "-p", help="Port"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the web dashboard."""
    import uvicorn

    # Sync server states on startup
    sync_server_states()

    console.print(f"[green]Starting MSM Web Dashboard[/green]")
    console.print(f"  URL: [cyan]http://{host}:{port}[/cyan]")
    console.print("  Press Ctrl+C to stop\n")

    uvicorn.run(
        "web.backend.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ============================================================================
# Config Commands
# ============================================================================

@config_app.command("show")
def show_config_cmd():
    """Show current configuration."""
    from msm_core.config import get_config

    config = get_config()
    console.print("\n[bold]MSM Configuration:[/bold]")
    for key, value in config.model_dump().items():
        console.print(f"  {key}: {value}")


@config_app.command("path")
def config_path_cmd():
    """Show configuration file path."""
    from msm_core.config import get_config_manager

    manager = get_config_manager()
    console.print(f"Config file: {manager.config_path}")


# ============================================================================
# Root Commands
# ============================================================================

@app.command("version")
def version_cmd():
    """Show MSM version."""
    from msm_core import __version__
    console.print(f"MSM (Minecraft Server Manager) v{__version__}")


@app.command("info")
def info_cmd():
    """Show system information."""
    import platform
    import psutil
    from platform_adapters import get_adapter

    adapter = get_adapter()

    console.print("\n[bold]System Information:[/bold]")
    console.print(f"  Platform: {platform.system()} {platform.release()}")
    console.print(f"  Python: {platform.python_version()}")
    console.print(f"  CPU Cores: {psutil.cpu_count()}")
    console.print(f"  Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")

    java_path = adapter.get_java_path()
    if java_path:
        console.print(f"  Java: {java_path}")
    else:
        console.print("  Java: [red]Not found[/red]")

    data_dir = adapter.user_data_dir("msm")
    console.print(f"  Data Dir: {data_dir}")


def main():
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
