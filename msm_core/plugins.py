"""Plugin management for MSM - handles plugin installation from Modrinth/Hangar."""
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

from .db import get_session, Server, Base
from .exceptions import MSMError
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger(__name__)

# API endpoints
MODRINTH_API = "https://api.modrinth.com/v2"
HANGAR_API = "https://hangar.papermc.io/api/v1"


class Plugin(Base):
    """Plugin model."""
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # modrinth, hangar, manual
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # modrinth/hangar project ID
    version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    installed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Plugin(name='{self.name}', server_id={self.server_id}, enabled={self.enabled})>"


class PluginError(MSMError):
    """Plugin-related errors."""
    pass


def search_modrinth(query: str, mc_version: Optional[str] = None, limit: int = 10) -> List[dict]:
    """Search for plugins on Modrinth.

    Args:
        query: Search query.
        mc_version: Optional Minecraft version filter.
        limit: Maximum results.

    Returns:
        List of plugin info dictionaries.
    """
    params = {
        "query": query,
        "limit": limit,
        "facets": '[[\"project_type:plugin\"]]',
    }

    if mc_version:
        params["facets"] = f'[[\"project_type:plugin\"],[\"versions:{mc_version}\"]]'

    try:
        response = requests.get(
            f"{MODRINTH_API}/search",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return [
            {
                "source": "modrinth",
                "id": hit["project_id"],
                "slug": hit["slug"],
                "name": hit["title"],
                "description": hit["description"],
                "author": hit["author"],
                "downloads": hit["downloads"],
                "icon_url": hit.get("icon_url"),
            }
            for hit in data.get("hits", [])
        ]

    except Exception as e:
        logger.error(f"Modrinth search failed: {e}")
        raise PluginError(f"Modrinth search failed: {e}")


def search_hangar(query: str, mc_version: Optional[str] = None, limit: int = 10) -> List[dict]:
    """Search for plugins on Hangar.

    Args:
        query: Search query.
        mc_version: Optional Minecraft version filter.
        limit: Maximum results.

    Returns:
        List of plugin info dictionaries.
    """
    params = {
        "q": query,
        "limit": limit,
        "platform": "PAPER",
    }

    try:
        response = requests.get(
            f"{HANGAR_API}/projects",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return [
            {
                "source": "hangar",
                "id": project["namespace"]["slug"],
                "slug": project["namespace"]["slug"],
                "name": project["name"],
                "description": project["description"],
                "author": project["namespace"]["owner"],
                "downloads": project["stats"]["downloads"],
                "icon_url": project.get("avatarUrl"),
            }
            for project in data.get("result", [])
        ]

    except Exception as e:
        logger.error(f"Hangar search failed: {e}")
        raise PluginError(f"Hangar search failed: {e}")


def get_modrinth_versions(project_id: str, mc_version: Optional[str] = None) -> List[dict]:
    """Get available versions for a Modrinth project.

    Args:
        project_id: Modrinth project ID or slug.
        mc_version: Optional Minecraft version filter.

    Returns:
        List of version info dictionaries.
    """
    params = {}
    if mc_version:
        params["game_versions"] = f'["{mc_version}"]'
    params["loaders"] = '["paper","spigot","bukkit"]'

    try:
        response = requests.get(
            f"{MODRINTH_API}/project/{project_id}/version",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        versions = response.json()

        return [
            {
                "id": v["id"],
                "name": v["name"],
                "version_number": v["version_number"],
                "game_versions": v["game_versions"],
                "loaders": v["loaders"],
                "downloads": v["downloads"],
                "file_name": v["files"][0]["filename"] if v["files"] else None,
                "file_url": v["files"][0]["url"] if v["files"] else None,
                "file_size": v["files"][0]["size"] if v["files"] else None,
            }
            for v in versions
        ]

    except Exception as e:
        logger.error(f"Failed to get Modrinth versions: {e}")
        raise PluginError(f"Failed to get Modrinth versions: {e}")


def install_from_modrinth(
    server_id: int,
    project_id: str,
    version_id: Optional[str] = None,
    mc_version: Optional[str] = None,
) -> dict:
    """Install a plugin from Modrinth.

    Args:
        server_id: The server database ID.
        project_id: Modrinth project ID or slug.
        version_id: Optional specific version ID.
        mc_version: Optional Minecraft version (to auto-select compatible version).

    Returns:
        Dictionary with plugin info.
    """
    # Get server info
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise PluginError(f"Server {server_id} not found")

        server_path = Path(server.path)
        server_mc_version = server.version

    # Get plugin versions
    versions = get_modrinth_versions(project_id, mc_version or server_mc_version)
    if not versions:
        raise PluginError(f"No compatible versions found for {project_id}")

    # Select version
    if version_id:
        version = next((v for v in versions if v["id"] == version_id), None)
        if not version:
            raise PluginError(f"Version {version_id} not found")
    else:
        version = versions[0]  # Latest compatible

    if not version.get("file_url"):
        raise PluginError("No download file available")

    # Download plugin
    plugins_dir = server_path / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    file_path = plugins_dir / version["file_name"]

    logger.info(f"Downloading {version['file_name']} from Modrinth...")
    response = requests.get(version["file_url"], stream=True, timeout=60)
    response.raise_for_status()

    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Plugin downloaded to {file_path}")

    # Get project info for name
    try:
        proj_response = requests.get(f"{MODRINTH_API}/project/{project_id}", timeout=30)
        proj_response.raise_for_status()
        project_info = proj_response.json()
        plugin_name = project_info["title"]
    except Exception:
        plugin_name = project_id

    # Record in database
    with get_session() as session:
        plugin = Plugin(
            server_id=server_id,
            name=plugin_name,
            source="modrinth",
            source_id=project_id,
            version=version["version_number"],
            file_path=str(file_path),
            file_name=version["file_name"],
            enabled=True,
        )
        session.add(plugin)
        session.flush()

        return {
            "id": plugin.id,
            "server_id": server_id,
            "name": plugin_name,
            "source": "modrinth",
            "source_id": project_id,
            "version": version["version_number"],
            "file_path": str(file_path),
            "file_name": version["file_name"],
        }


def install_from_url(
    server_id: int,
    url: str,
    name: Optional[str] = None,
) -> dict:
    """Install a plugin from a direct URL.

    Args:
        server_id: The server database ID.
        url: Direct download URL for the plugin JAR.
        name: Optional plugin name (extracted from URL if not provided).

    Returns:
        Dictionary with plugin info.
    """
    # Get server info
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise PluginError(f"Server {server_id} not found")

        server_path = Path(server.path)

    # Download plugin
    plugins_dir = server_path / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    # Get filename from URL
    file_name = url.split("/")[-1].split("?")[0]
    if not file_name.endswith(".jar"):
        file_name += ".jar"

    file_path = plugins_dir / file_name

    logger.info(f"Downloading plugin from {url}...")
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Plugin downloaded to {file_path}")

    plugin_name = name or file_name.replace(".jar", "")

    # Record in database
    with get_session() as session:
        plugin = Plugin(
            server_id=server_id,
            name=plugin_name,
            source="manual",
            source_id=None,
            version=None,
            file_path=str(file_path),
            file_name=file_name,
            enabled=True,
        )
        session.add(plugin)
        session.flush()

        return {
            "id": plugin.id,
            "server_id": server_id,
            "name": plugin_name,
            "source": "manual",
            "file_path": str(file_path),
            "file_name": file_name,
        }


def install_plugin(server_id: int, plugin_url: str) -> bool:
    """Install a plugin from URL (legacy function).

    Args:
        server_id: The server database ID.
        plugin_url: URL to download plugin from.

    Returns:
        True if successful.
    """
    try:
        install_from_url(server_id, plugin_url)
        return True
    except Exception as e:
        logger.error(f"Plugin installation failed: {e}")
        return False


def uninstall_plugin(plugin_id: int, delete_file: bool = True) -> bool:
    """Uninstall a plugin.

    Args:
        plugin_id: The plugin database ID.
        delete_file: Whether to delete the plugin file.

    Returns:
        True if successful.
    """
    with get_session() as session:
        plugin = session.query(Plugin).filter(Plugin.id == plugin_id).first()
        if not plugin:
            raise PluginError(f"Plugin {plugin_id} not found")

        file_path = Path(plugin.file_path)

        if delete_file and file_path.exists():
            logger.info(f"Deleting plugin file: {file_path}")
            file_path.unlink()

        session.delete(plugin)
        logger.info(f"Uninstalled plugin {plugin_id}")

        return True


def toggle_plugin(plugin_id: int, enabled: bool) -> dict:
    """Enable or disable a plugin.

    Disabled plugins are moved to plugins/disabled/ folder.

    Args:
        plugin_id: The plugin database ID.
        enabled: Enable or disable.

    Returns:
        Updated plugin dictionary.
    """
    with get_session() as session:
        plugin = session.query(Plugin).filter(Plugin.id == plugin_id).first()
        if not plugin:
            raise PluginError(f"Plugin {plugin_id} not found")

        current_path = Path(plugin.file_path)
        if not current_path.exists():
            raise PluginError(f"Plugin file not found: {current_path}")

        plugins_dir = current_path.parent
        if plugins_dir.name == "disabled":
            plugins_dir = plugins_dir.parent

        disabled_dir = plugins_dir / "disabled"

        if enabled and not plugin.enabled:
            # Move from disabled to plugins
            new_path = plugins_dir / plugin.file_name
            shutil.move(str(current_path), str(new_path))
            plugin.file_path = str(new_path)
            plugin.enabled = True
            logger.info(f"Enabled plugin: {plugin.name}")

        elif not enabled and plugin.enabled:
            # Move to disabled folder
            disabled_dir.mkdir(exist_ok=True)
            new_path = disabled_dir / plugin.file_name
            shutil.move(str(current_path), str(new_path))
            plugin.file_path = str(new_path)
            plugin.enabled = False
            logger.info(f"Disabled plugin: {plugin.name}")

        return {
            "id": plugin.id,
            "server_id": plugin.server_id,
            "name": plugin.name,
            "source": plugin.source,
            "version": plugin.version,
            "file_path": plugin.file_path,
            "enabled": plugin.enabled,
        }


def list_plugins(server_id: int) -> List[dict]:
    """List all plugins for a server.

    Args:
        server_id: The server database ID.

    Returns:
        List of plugin dictionaries.
    """
    with get_session() as session:
        plugins = (
            session.query(Plugin)
            .filter(Plugin.server_id == server_id)
            .order_by(Plugin.name)
            .all()
        )

        return [
            {
                "id": p.id,
                "server_id": p.server_id,
                "name": p.name,
                "source": p.source,
                "source_id": p.source_id,
                "version": p.version,
                "file_path": p.file_path,
                "file_name": p.file_name,
                "installed_at": p.installed_at.isoformat() if p.installed_at else None,
                "enabled": p.enabled,
                "exists": Path(p.file_path).exists(),
            }
            for p in plugins
        ]


def get_plugin_by_id(plugin_id: int) -> Optional[dict]:
    """Get a plugin by ID.

    Args:
        plugin_id: The plugin database ID.

    Returns:
        Plugin dictionary or None.
    """
    with get_session() as session:
        plugin = session.query(Plugin).filter(Plugin.id == plugin_id).first()
        if not plugin:
            return None

        return {
            "id": plugin.id,
            "server_id": plugin.server_id,
            "name": plugin.name,
            "source": plugin.source,
            "source_id": plugin.source_id,
            "version": plugin.version,
            "file_path": plugin.file_path,
            "file_name": plugin.file_name,
            "installed_at": plugin.installed_at.isoformat() if plugin.installed_at else None,
            "enabled": plugin.enabled,
            "exists": Path(plugin.file_path).exists(),
        }


def check_plugin_updates(server_id: int) -> List[dict]:
    """Check for plugin updates.

    Args:
        server_id: The server database ID.

    Returns:
        List of plugins with available updates.
    """
    updates = []

    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            return []

        plugins = (
            session.query(Plugin)
            .filter(Plugin.server_id == server_id)
            .filter(Plugin.source == "modrinth")
            .filter(Plugin.source_id.isnot(None))
            .all()
        )

        for plugin in plugins:
            try:
                versions = get_modrinth_versions(plugin.source_id, server.version)
                if versions and versions[0]["version_number"] != plugin.version:
                    updates.append({
                        "plugin_id": plugin.id,
                        "name": plugin.name,
                        "current_version": plugin.version,
                        "latest_version": versions[0]["version_number"],
                        "source": "modrinth",
                    })
            except Exception as e:
                logger.warning(f"Failed to check updates for {plugin.name}: {e}")

    return updates
