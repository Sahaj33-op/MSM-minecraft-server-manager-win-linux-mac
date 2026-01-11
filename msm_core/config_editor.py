"""Configuration file editor for Minecraft servers."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import get_session, Server
from .exceptions import MSMError

logger = logging.getLogger(__name__)


class ConfigError(MSMError):
    """Configuration-related errors."""
    pass


class ServerPropertiesEditor:
    """Editor for server.properties files."""

    # Common server.properties keys with their types and descriptions
    PROPERTY_SCHEMA = {
        "allow-flight": {"type": "bool", "default": False, "description": "Allow players to fly"},
        "allow-nether": {"type": "bool", "default": True, "description": "Allow the Nether dimension"},
        "broadcast-console-to-ops": {"type": "bool", "default": True, "description": "Broadcast console to ops"},
        "broadcast-rcon-to-ops": {"type": "bool", "default": True, "description": "Broadcast RCON to ops"},
        "difficulty": {"type": "enum", "values": ["peaceful", "easy", "normal", "hard"], "default": "easy"},
        "enable-command-block": {"type": "bool", "default": False, "description": "Enable command blocks"},
        "enable-jmx-monitoring": {"type": "bool", "default": False, "description": "Enable JMX monitoring"},
        "enable-query": {"type": "bool", "default": False, "description": "Enable GameSpy4 query"},
        "enable-rcon": {"type": "bool", "default": False, "description": "Enable remote console"},
        "enable-status": {"type": "bool", "default": True, "description": "Enable server status in list"},
        "enforce-secure-profile": {"type": "bool", "default": True, "description": "Enforce secure profiles"},
        "enforce-whitelist": {"type": "bool", "default": False, "description": "Enforce whitelist"},
        "entity-broadcast-range-percentage": {"type": "int", "min": 10, "max": 1000, "default": 100},
        "force-gamemode": {"type": "bool", "default": False, "description": "Force default gamemode"},
        "function-permission-level": {"type": "int", "min": 1, "max": 4, "default": 2},
        "gamemode": {"type": "enum", "values": ["survival", "creative", "adventure", "spectator"], "default": "survival"},
        "generate-structures": {"type": "bool", "default": True, "description": "Generate structures"},
        "generator-settings": {"type": "string", "default": "{}", "description": "World generator settings"},
        "hardcore": {"type": "bool", "default": False, "description": "Hardcore mode"},
        "hide-online-players": {"type": "bool", "default": False, "description": "Hide online player count"},
        "initial-disabled-packs": {"type": "string", "default": "", "description": "Initially disabled packs"},
        "initial-enabled-packs": {"type": "string", "default": "vanilla", "description": "Initially enabled packs"},
        "level-name": {"type": "string", "default": "world", "description": "World folder name"},
        "level-seed": {"type": "string", "default": "", "description": "World seed"},
        "level-type": {"type": "string", "default": "minecraft:normal", "description": "World type"},
        "max-chained-neighbor-updates": {"type": "int", "default": 1000000},
        "max-players": {"type": "int", "min": 0, "max": 2147483647, "default": 20, "description": "Maximum players"},
        "max-tick-time": {"type": "int", "default": 60000, "description": "Max tick time before watchdog"},
        "max-world-size": {"type": "int", "min": 1, "max": 29999984, "default": 29999984},
        "motd": {"type": "string", "default": "A Minecraft Server", "description": "Server message of the day"},
        "network-compression-threshold": {"type": "int", "default": 256},
        "online-mode": {"type": "bool", "default": True, "description": "Verify player accounts with Mojang"},
        "op-permission-level": {"type": "int", "min": 0, "max": 4, "default": 4},
        "player-idle-timeout": {"type": "int", "min": 0, "default": 0, "description": "Kick idle players (minutes)"},
        "prevent-proxy-connections": {"type": "bool", "default": False},
        "pvp": {"type": "bool", "default": True, "description": "Enable player vs player"},
        "query.port": {"type": "int", "min": 1, "max": 65535, "default": 25565},
        "rate-limit": {"type": "int", "default": 0, "description": "Packet rate limit"},
        "rcon.password": {"type": "string", "default": "", "description": "RCON password"},
        "rcon.port": {"type": "int", "min": 1, "max": 65535, "default": 25575},
        "require-resource-pack": {"type": "bool", "default": False},
        "resource-pack": {"type": "string", "default": "", "description": "Resource pack URL"},
        "resource-pack-prompt": {"type": "string", "default": ""},
        "resource-pack-sha1": {"type": "string", "default": ""},
        "server-ip": {"type": "string", "default": "", "description": "Server bind IP"},
        "server-port": {"type": "int", "min": 1, "max": 65535, "default": 25565, "description": "Server port"},
        "simulation-distance": {"type": "int", "min": 3, "max": 32, "default": 10},
        "spawn-animals": {"type": "bool", "default": True, "description": "Spawn animals"},
        "spawn-monsters": {"type": "bool", "default": True, "description": "Spawn monsters"},
        "spawn-npcs": {"type": "bool", "default": True, "description": "Spawn NPCs (villagers)"},
        "spawn-protection": {"type": "int", "min": 0, "default": 16, "description": "Spawn protection radius"},
        "sync-chunk-writes": {"type": "bool", "default": True},
        "text-filtering-config": {"type": "string", "default": ""},
        "use-native-transport": {"type": "bool", "default": True},
        "view-distance": {"type": "int", "min": 3, "max": 32, "default": 10, "description": "View distance (chunks)"},
        "white-list": {"type": "bool", "default": False, "description": "Enable whitelist"},
    }

    def __init__(self, server_path: Path):
        """Initialize the editor.

        Args:
            server_path: Path to the server directory.
        """
        self.server_path = Path(server_path)
        self.path = self.server_path / "server.properties"
        self._properties: Dict[str, str] = {}
        self._comments: List[str] = []
        self._loaded = False

    def load(self) -> Dict[str, str]:
        """Load properties from file.

        Returns:
            Dictionary of property key-value pairs.
        """
        self._properties = {}
        self._comments = []

        if not self.path.exists():
            self._loaded = True
            return self._properties

        try:
            content = self.path.read_text(encoding="utf-8")

            for line in content.splitlines():
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Store comments
                if line.startswith("#"):
                    self._comments.append(line)
                    continue

                # Parse property
                if "=" in line:
                    key, value = line.split("=", 1)
                    self._properties[key.strip()] = value.strip()

            self._loaded = True
            return self._properties

        except Exception as e:
            raise ConfigError(f"Failed to load server.properties: {e}")

    def save(self) -> None:
        """Save properties to file."""
        if not self._loaded:
            self.load()

        try:
            lines = []

            # Add header comment
            lines.append("#Minecraft server properties")
            lines.append("#Generated by MSM")
            lines.append("")

            # Add properties sorted alphabetically
            for key in sorted(self._properties.keys()):
                value = self._properties[key]
                lines.append(f"{key}={value}")

            self.path.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"Saved server.properties to {self.path}")

        except Exception as e:
            raise ConfigError(f"Failed to save server.properties: {e}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a property value.

        Args:
            key: Property key.
            default: Default value if not found.

        Returns:
            Property value or default.
        """
        if not self._loaded:
            self.load()
        return self._properties.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a property value.

        Args:
            key: Property key.
            value: Property value (will be converted to string).
        """
        if not self._loaded:
            self.load()

        # Convert boolean values
        if isinstance(value, bool):
            value = "true" if value else "false"

        self._properties[key] = str(value)

    def delete(self, key: str) -> bool:
        """Delete a property.

        Args:
            key: Property key to delete.

        Returns:
            True if key was deleted, False if not found.
        """
        if not self._loaded:
            self.load()

        if key in self._properties:
            del self._properties[key]
            return True
        return False

    def get_all(self) -> Dict[str, str]:
        """Get all properties.

        Returns:
            Dictionary of all properties.
        """
        if not self._loaded:
            self.load()
        return dict(self._properties)

    def set_multiple(self, updates: Dict[str, Any]) -> None:
        """Set multiple properties at once.

        Args:
            updates: Dictionary of key-value pairs to set.
        """
        for key, value in updates.items():
            self.set(key, value)

    def validate(self, key: str, value: Any) -> bool:
        """Validate a property value against the schema.

        Args:
            key: Property key.
            value: Value to validate.

        Returns:
            True if valid, False otherwise.
        """
        if key not in self.PROPERTY_SCHEMA:
            return True  # Unknown properties are allowed

        schema = self.PROPERTY_SCHEMA[key]
        prop_type = schema.get("type", "string")

        try:
            if prop_type == "bool":
                if isinstance(value, bool):
                    return True
                if isinstance(value, str):
                    return value.lower() in ("true", "false")
                return False

            elif prop_type == "int":
                int_val = int(value)
                min_val = schema.get("min", float("-inf"))
                max_val = schema.get("max", float("inf"))
                return min_val <= int_val <= max_val

            elif prop_type == "enum":
                values = schema.get("values", [])
                return str(value).lower() in [v.lower() for v in values]

            elif prop_type == "string":
                return True

            return True

        except (ValueError, TypeError):
            return False

    def get_schema(self) -> Dict[str, dict]:
        """Get the property schema.

        Returns:
            Dictionary of property schemas.
        """
        return self.PROPERTY_SCHEMA


def get_server_properties(server_id: int) -> Dict[str, str]:
    """Get server.properties for a server.

    Args:
        server_id: The server database ID.

    Returns:
        Dictionary of properties.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ConfigError(f"Server {server_id} not found")

        editor = ServerPropertiesEditor(Path(server.path))
        return editor.get_all()


def update_server_properties(server_id: int, updates: Dict[str, Any]) -> Dict[str, str]:
    """Update server.properties for a server.

    Args:
        server_id: The server database ID.
        updates: Dictionary of properties to update.

    Returns:
        Updated properties dictionary.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ConfigError(f"Server {server_id} not found")

        editor = ServerPropertiesEditor(Path(server.path))
        editor.set_multiple(updates)
        editor.save()

        return editor.get_all()


def get_property_schema() -> Dict[str, dict]:
    """Get the server.properties schema.

    Returns:
        Dictionary of property schemas with types, defaults, and descriptions.
    """
    return ServerPropertiesEditor.PROPERTY_SCHEMA
