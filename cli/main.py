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
