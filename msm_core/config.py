"""Configuration management for MSM."""
import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MSMConfig(BaseModel):
    """Global MSM Configuration."""

    data_dir: str = Field(default="~/.msm", description="Root directory for MSM data")
    default_java_memory: str = Field(default="2G", description="Default memory for servers")
    default_port: int = Field(default=25565, description="Default server port")
    web_host: str = Field(default="127.0.0.1", description="Web UI bind address")
    web_port: int = Field(default=5000, description="Web UI port")
    log_level: str = Field(default="INFO", description="Logging level")
    auto_accept_eula: bool = Field(default=True, description="Automatically accept Minecraft EULA")
    check_java_on_startup: bool = Field(default=True, description="Check Java availability on startup")


class ConfigManager:
    """Manages loading and saving of configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the config manager.

        Args:
            config_path: Path to the config file. If None, uses default location.
        """
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = Path.home() / ".msm" / "config.json"

        self._config: Optional[MSMConfig] = None

    @property
    def config(self) -> MSMConfig:
        """Get the current configuration (lazy loading)."""
        if self._config is None:
            self._load()
        return self._config  # type: ignore

    def _load(self) -> None:
        """Load config from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self._config = MSMConfig(**data)
                    logger.debug(f"Configuration loaded from {self.config_path}")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid config file, using defaults: {e}")
                self._config = MSMConfig()
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._config = MSMConfig()
        else:
            logger.debug("No config file found, using defaults")
            self._config = MSMConfig()

    def save(self) -> None:
        """Save config to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            f.write(self.config.model_dump_json(indent=2))
        logger.debug(f"Configuration saved to {self.config_path}")

    def get(self) -> MSMConfig:
        """Get the current configuration."""
        return self.config

    def update(self, **kwargs) -> None:
        """Update configuration values.

        Args:
            **kwargs: Configuration values to update.
        """
        current = self.config.model_dump()
        current.update(kwargs)
        self._config = MSMConfig(**current)

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = MSMConfig()


# Lazy singleton pattern
_config_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance (lazy initialization)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def get_config() -> MSMConfig:
    """Get the current configuration."""
    return get_config_manager().config


def reset_config() -> None:
    """Reset the global config instance. Useful for testing."""
    global _config_instance
    _config_instance = None
