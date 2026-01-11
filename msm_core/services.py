"""Platform service management for MSM - creates background services for Minecraft servers."""
import getpass
import logging
import os
import platform
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from msm_core.db import get_session, Server
from msm_core.exceptions import MSMError

logger = logging.getLogger(__name__)


def _is_running_as_root() -> bool:
    """Check if the current process is running as root/Administrator.

    Returns:
        True if running as root (Unix) or Administrator (Windows).
    """
    if platform.system() == "Windows":
        try:
            # Windows: check if running as Administrator
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix: check effective UID
        return os.geteuid() == 0


def _check_root_safety(operation: str) -> None:
    """Check if running as root and warn/fail for dangerous operations.

    Args:
        operation: Description of the operation being performed.

    Raises:
        ServiceError: If running as root and operation is dangerous.
    """
    if _is_running_as_root():
        logger.warning(
            f"SECURITY WARNING: {operation} is being run as root/Administrator. "
            "This is dangerous as Minecraft servers should NOT run with elevated privileges. "
            "A malicious plugin could compromise your entire system."
        )
        raise ServiceError(
            f"Cannot {operation} as root/Administrator. "
            "Minecraft servers should run as a non-privileged user. "
            "Please run MSM as a regular user, not with sudo or as Administrator."
        )


class ServiceError(MSMError):
    """Service management errors."""
    pass


# ============================================================================
# Systemd Templates (Linux)
# ============================================================================

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Minecraft Server - {name}
After=network.target
Documentation=https://github.com/your-repo/msm

[Service]
Type=simple
User={user}
WorkingDirectory={server_path}
ExecStart={java_path} {jvm_args} -jar {jar_name} nogui
ExecStop=/bin/sh -c "echo 'stop' > /proc/$MAINPID/fd/0 || kill -TERM $MAINPID"
Restart=on-failure
RestartSec=30
StandardInput=socket
StandardOutput=journal
StandardError=journal
SyslogIdentifier=msm-{name}

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={server_path}
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_SOCKET_TEMPLATE = """[Unit]
Description=Minecraft Server Socket - {name}
PartOf=msm-{name}.service

[Socket]
ListenFIFO={server_path}/server.stdin

[Install]
WantedBy=sockets.target
"""

# ============================================================================
# Launchd Templates (macOS)
# ============================================================================

LAUNCHD_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.msm.{name}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{java_path}</string>
{jvm_args_array}
        <string>-jar</string>
        <string>{jar_name}</string>
        <string>nogui</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{server_path}</string>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>{server_path}/logs/launchd.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{server_path}/logs/launchd.stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
"""

# ============================================================================
# Windows Service Template (NSSM)
# ============================================================================

WINDOWS_NSSM_SCRIPT = """@echo off
REM MSM Windows Service Setup Script for {name}
REM Requires NSSM (https://nssm.cc) to be installed

set SERVICE_NAME=MSM-{name}
set JAVA_PATH={java_path}
set SERVER_PATH={server_path}
set JAR_NAME={jar_name}
set JVM_ARGS={jvm_args}

REM Install the service
nssm install %SERVICE_NAME% "%JAVA_PATH%"
nssm set %SERVICE_NAME% AppDirectory "%SERVER_PATH%"
nssm set %SERVICE_NAME% AppParameters %JVM_ARGS% -jar %JAR_NAME% nogui
nssm set %SERVICE_NAME% DisplayName "Minecraft Server - {name}"
nssm set %SERVICE_NAME% Description "Minecraft server managed by MSM"
nssm set %SERVICE_NAME% Start SERVICE_DEMAND_START
nssm set %SERVICE_NAME% AppStdout "%SERVER_PATH%\\logs\\service.stdout.log"
nssm set %SERVICE_NAME% AppStderr "%SERVER_PATH%\\logs\\service.stderr.log"
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateBytes 10485760

echo Service %SERVICE_NAME% installed successfully!
echo Start with: nssm start %SERVICE_NAME%
echo Stop with: nssm stop %SERVICE_NAME%
echo Remove with: nssm remove %SERVICE_NAME%
"""


def get_service_name(server_name: str) -> str:
    """Get the service name for a server.

    Args:
        server_name: The server name.

    Returns:
        Service name (sanitized).
    """
    # Sanitize the name for use in service names
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in server_name)
    return f"msm-{safe_name}"


def find_jar_file(server_path: Path) -> Optional[str]:
    """Find the server JAR file in a server directory.

    Uses a smart heuristic:
    1. Check for common server jar names first
    2. Look for jars with Main-Class manifest entries
    3. Exclude library jars (in lib/, libraries/, mods/)
    4. Sort by file size (server jars are usually larger)

    Args:
        server_path: Path to server directory.

    Returns:
        JAR filename or None.
    """
    # Priority order of common server jar names
    common_names = [
        "server.jar",
        "paper.jar",
        "purpur.jar",
        "spigot.jar",
        "fabric-server-launch.jar",
        "forge.jar",
        "minecraft_server.jar",
    ]

    for name in common_names:
        if (server_path / name).exists():
            return name

    # Find all jar files in the root directory only (not subdirectories)
    jar_files = [
        f for f in server_path.glob("*.jar")
        if f.is_file()
    ]

    if not jar_files:
        return None

    # Try to find a jar with a manifest indicating it's runnable
    for jar_path in jar_files:
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                if 'META-INF/MANIFEST.MF' in zf.namelist():
                    manifest = zf.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore')
                    if 'Main-Class' in manifest:
                        # This jar is likely runnable
                        return jar_path.name
        except (zipfile.BadZipFile, OSError):
            continue

    # Fallback: return the largest jar (server jars are typically larger than libraries)
    jar_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    return jar_files[0].name


def create_systemd_service(server_id: int) -> dict:
    """Create a systemd service for a Minecraft server (Linux).

    Args:
        server_id: The server database ID.

    Returns:
        Dictionary with service info.

    Raises:
        ServiceError: If service creation fails or running as root.
    """
    if platform.system() != "Linux":
        raise ServiceError("systemd services are only available on Linux")

    # SECURITY: Prevent creating services as root
    _check_root_safety("create systemd service")

    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ServiceError(f"Server {server_id} not found")

        server_name = server.name
        server_path = Path(server.path)
        java_path = server.java_path or "java"
        memory = server.memory or "2G"
        jvm_args = server.jvm_args or f"-Xmx{memory} -Xms{memory}"

    jar_name = find_jar_file(server_path)
    if not jar_name:
        raise ServiceError(f"No JAR file found in {server_path}")

    service_name = get_service_name(server_name)
    current_user = getpass.getuser()

    # Generate service content
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        name=server_name,
        user=current_user,
        server_path=str(server_path),
        java_path=java_path,
        jvm_args=jvm_args,
        jar_name=jar_name,
    )

    # Write to user's systemd directory
    user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    user_systemd_dir.mkdir(parents=True, exist_ok=True)

    service_path = user_systemd_dir / f"{service_name}.service"
    service_path.write_text(service_content)

    logger.info(f"Created systemd service: {service_path}")

    # Reload systemd
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to reload systemd: {e}")

    return {
        "service_name": service_name,
        "service_path": str(service_path),
        "type": "systemd",
        "commands": {
            "enable": f"systemctl --user enable {service_name}",
            "start": f"systemctl --user start {service_name}",
            "stop": f"systemctl --user stop {service_name}",
            "status": f"systemctl --user status {service_name}",
            "logs": f"journalctl --user -u {service_name} -f",
        },
    }


def create_launchd_service(server_id: int) -> dict:
    """Create a launchd plist for a Minecraft server (macOS).

    Args:
        server_id: The server database ID.

    Returns:
        Dictionary with service info.

    Raises:
        ServiceError: If service creation fails.
    """
    if platform.system() != "Darwin":
        raise ServiceError("launchd services are only available on macOS")

    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ServiceError(f"Server {server_id} not found")

        server_name = server.name
        server_path = Path(server.path)
        java_path = server.java_path or "/usr/bin/java"
        memory = server.memory or "2G"
        jvm_args = server.jvm_args or f"-Xmx{memory} -Xms{memory}"

    jar_name = find_jar_file(server_path)
    if not jar_name:
        raise ServiceError(f"No JAR file found in {server_path}")

    # Create logs directory
    (server_path / "logs").mkdir(exist_ok=True)

    # Convert JVM args to plist array format
    jvm_args_list = jvm_args.split()
    jvm_args_array = "\n".join(f"        <string>{arg}</string>" for arg in jvm_args_list)

    # Generate plist content
    plist_content = LAUNCHD_PLIST_TEMPLATE.format(
        name=server_name.replace(" ", "_"),
        server_path=str(server_path),
        java_path=java_path,
        jvm_args_array=jvm_args_array,
        jar_name=jar_name,
    )

    # Write to LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    service_name = f"com.msm.{server_name.replace(' ', '_')}"
    plist_path = launch_agents_dir / f"{service_name}.plist"
    plist_path.write_text(plist_content)

    logger.info(f"Created launchd plist: {plist_path}")

    return {
        "service_name": service_name,
        "service_path": str(plist_path),
        "type": "launchd",
        "commands": {
            "load": f"launchctl load {plist_path}",
            "unload": f"launchctl unload {plist_path}",
            "start": f"launchctl start {service_name}",
            "stop": f"launchctl stop {service_name}",
            "status": f"launchctl list | grep {service_name}",
        },
    }


def create_windows_service_script(server_id: int) -> dict:
    """Create a Windows NSSM service script for a Minecraft server.

    Args:
        server_id: The server database ID.

    Returns:
        Dictionary with script info.

    Raises:
        ServiceError: If script creation fails.
    """
    if platform.system() != "Windows":
        raise ServiceError("Windows service scripts are only available on Windows")

    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ServiceError(f"Server {server_id} not found")

        server_name = server.name
        server_path = Path(server.path)
        java_path = server.java_path or "java"
        memory = server.memory or "2G"
        jvm_args = server.jvm_args or f"-Xmx{memory} -Xms{memory}"

    jar_name = find_jar_file(server_path)
    if not jar_name:
        raise ServiceError(f"No JAR file found in {server_path}")

    # Create logs directory
    (server_path / "logs").mkdir(exist_ok=True)

    # Generate script content
    script_content = WINDOWS_NSSM_SCRIPT.format(
        name=server_name.replace(" ", "_"),
        server_path=str(server_path),
        java_path=java_path,
        jvm_args=jvm_args,
        jar_name=jar_name,
    )

    # Write script to server directory
    script_path = server_path / "install_service.bat"
    script_path.write_text(script_content)

    logger.info(f"Created Windows service script: {script_path}")

    return {
        "service_name": f"MSM-{server_name}",
        "script_path": str(script_path),
        "type": "nssm",
        "note": "Requires NSSM (https://nssm.cc) to be installed",
        "commands": {
            "install": f"Run {script_path} as Administrator",
            "start": f"nssm start MSM-{server_name}",
            "stop": f"nssm stop MSM-{server_name}",
            "status": f"nssm status MSM-{server_name}",
            "remove": f"nssm remove MSM-{server_name}",
        },
    }


def create_service(server_id: int) -> dict:
    """Create a platform-appropriate background service for a Minecraft server.

    Args:
        server_id: The server database ID.

    Returns:
        Dictionary with service info.
    """
    system = platform.system()

    if system == "Linux":
        return create_systemd_service(server_id)
    elif system == "Darwin":
        return create_launchd_service(server_id)
    elif system == "Windows":
        return create_windows_service_script(server_id)
    else:
        raise ServiceError(f"Unsupported platform: {system}")


def remove_systemd_service(server_name: str) -> bool:
    """Remove a systemd service.

    Args:
        server_name: The server name.

    Returns:
        True if removed successfully.
    """
    if platform.system() != "Linux":
        return False

    service_name = get_service_name(server_name)
    service_path = Path.home() / ".config" / "systemd" / "user" / f"{service_name}.service"

    if service_path.exists():
        # Stop and disable first
        subprocess.run(["systemctl", "--user", "stop", service_name], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", service_name], capture_output=True)

        service_path.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

        logger.info(f"Removed systemd service: {service_name}")
        return True

    return False


def remove_launchd_service(server_name: str) -> bool:
    """Remove a launchd service.

    Args:
        server_name: The server name.

    Returns:
        True if removed successfully.
    """
    if platform.system() != "Darwin":
        return False

    service_name = f"com.msm.{server_name.replace(' ', '_')}"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{service_name}.plist"

    if plist_path.exists():
        # Unload first
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

        plist_path.unlink()

        logger.info(f"Removed launchd service: {service_name}")
        return True

    return False


def remove_service(server_name: str) -> bool:
    """Remove a platform-appropriate service for a server.

    Args:
        server_name: The server name.

    Returns:
        True if removed successfully.
    """
    system = platform.system()

    if system == "Linux":
        return remove_systemd_service(server_name)
    elif system == "Darwin":
        return remove_launchd_service(server_name)
    else:
        # Windows: Just inform user to run removal command
        logger.info(f"To remove Windows service, run: nssm remove MSM-{server_name}")
        return False


def get_service_status(server_name: str) -> Optional[dict]:
    """Get the status of a background service.

    Args:
        server_name: The server name.

    Returns:
        Dictionary with status info or None if no service.
    """
    system = platform.system()

    if system == "Linux":
        service_name = get_service_name(server_name)
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", service_name],
                capture_output=True,
                text=True,
            )
            is_active = result.stdout.strip() == "active"

            return {
                "type": "systemd",
                "service_name": service_name,
                "is_active": is_active,
                "status": result.stdout.strip(),
            }
        except Exception:
            return None

    elif system == "Darwin":
        service_name = f"com.msm.{server_name.replace(' ', '_')}"
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
            )
            is_active = service_name in result.stdout

            return {
                "type": "launchd",
                "service_name": service_name,
                "is_active": is_active,
            }
        except Exception:
            return None

    return None
