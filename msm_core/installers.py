"""Server installation and download management for MSM."""
import logging
from pathlib import Path
from typing import Optional

import requests

from .utils import calculate_sha256
from .exceptions import DownloadError, ChecksumError, UnsupportedServerTypeError

logger = logging.getLogger(__name__)

# API endpoints
PAPER_API = "https://api.papermc.io/v2"
MOJANG_VERSION_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
FABRIC_META = "https://meta.fabricmc.net/v2"
PURPUR_API = "https://api.purpurmc.org/v2"

# Request timeout
TIMEOUT = 30


def download_file(url: str, dest: Path, expected_sha256: Optional[str] = None) -> bool:
    """Download a file with optional checksum verification.

    Args:
        url: URL to download from.
        dest: Destination path.
        expected_sha256: Expected SHA256 hash (optional).

    Returns:
        True if download was successful.

    Raises:
        DownloadError: If the download fails.
        ChecksumError: If checksum verification fails.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Downloading {url}")
        response = requests.get(url, stream=True, timeout=TIMEOUT)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    if downloaded % (1024 * 1024) == 0:  # Log every MB
                        logger.debug(f"Download progress: {percent:.1f}%")

        logger.info(f"Downloaded {dest.name} ({downloaded} bytes)")

        # Verify checksum if provided
        if expected_sha256:
            actual_sha256 = calculate_sha256(dest)
            if actual_sha256.lower() != expected_sha256.lower():
                dest.unlink()  # Remove corrupted file
                raise ChecksumError(expected_sha256, actual_sha256)
            logger.debug("Checksum verified")

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        raise DownloadError(url, str(e))


def install_paper(version: str, install_dir: Path) -> bool:
    """Install Paper server.

    Args:
        version: Minecraft version (e.g., "1.20.4").
        install_dir: Directory to install to.

    Returns:
        True if installation was successful.
    """
    try:
        # Get builds for this version
        builds_url = f"{PAPER_API}/projects/paper/versions/{version}/builds"
        logger.info(f"Fetching Paper builds for {version}")

        response = requests.get(builds_url, timeout=TIMEOUT)
        response.raise_for_status()
        builds_data = response.json()

        if not builds_data.get("builds"):
            logger.error(f"No Paper builds found for version {version}")
            return False

        # Get the latest build
        latest_build = builds_data["builds"][-1]
        build_number = latest_build["build"]
        download_info = latest_build["downloads"]["application"]
        jar_name = download_info["name"]
        sha256 = download_info["sha256"]

        # Construct download URL
        download_url = f"{PAPER_API}/projects/paper/versions/{version}/builds/{build_number}/downloads/{jar_name}"

        # Download the JAR
        jar_path = install_dir / "server.jar"
        download_file(download_url, jar_path, sha256)

        logger.info(f"Paper {version} (build {build_number}) installed successfully")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Paper version {version} not found")
        else:
            logger.error(f"Failed to fetch Paper builds: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to install Paper: {e}")
        return False


def install_vanilla(version: str, install_dir: Path) -> bool:
    """Install Vanilla server.

    Args:
        version: Minecraft version (e.g., "1.20.4").
        install_dir: Directory to install to.

    Returns:
        True if installation was successful.
    """
    try:
        # Get version manifest
        logger.info("Fetching Minecraft version manifest")
        response = requests.get(MOJANG_VERSION_MANIFEST, timeout=TIMEOUT)
        response.raise_for_status()
        manifest = response.json()

        # Find the version
        version_info = None
        for v in manifest["versions"]:
            if v["id"] == version:
                version_info = v
                break

        if not version_info:
            logger.error(f"Minecraft version {version} not found")
            return False

        # Get version details
        logger.info(f"Fetching version details for {version}")
        version_response = requests.get(version_info["url"], timeout=TIMEOUT)
        version_response.raise_for_status()
        version_data = version_response.json()

        # Get server download info
        server_info = version_data.get("downloads", {}).get("server")
        if not server_info:
            logger.error(f"No server download available for version {version}")
            return False

        download_url = server_info["url"]
        _sha1 = server_info.get("sha1")  # Mojang uses SHA1 (unused, kept for future verification)

        # Download the JAR
        jar_path = install_dir / "server.jar"

        # Note: Mojang uses SHA1, not SHA256, so we skip verification
        # or could implement SHA1 check
        download_file(download_url, jar_path)

        logger.info(f"Vanilla {version} installed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to install Vanilla: {e}")
        return False


def install_fabric(version: str, install_dir: Path) -> bool:
    """Install Fabric server.

    Args:
        version: Minecraft version (e.g., "1.20.4").
        install_dir: Directory to install to.

    Returns:
        True if installation was successful.
    """
    try:
        # Get latest loader version
        loader_url = f"{FABRIC_META}/versions/loader"
        response = requests.get(loader_url, timeout=TIMEOUT)
        response.raise_for_status()
        loaders = response.json()

        if not loaders:
            logger.error("No Fabric loader versions found")
            return False

        # Use latest stable loader
        loader_version = None
        for loader in loaders:
            if loader.get("stable", False):
                loader_version = loader["version"]
                break

        if not loader_version:
            loader_version = loaders[0]["version"]

        # Get latest installer version
        installer_url = f"{FABRIC_META}/versions/installer"
        response = requests.get(installer_url, timeout=TIMEOUT)
        response.raise_for_status()
        installers = response.json()

        if not installers:
            logger.error("No Fabric installer versions found")
            return False

        installer_version = installers[0]["version"]

        # Download server JAR directly
        server_url = f"{FABRIC_META}/versions/loader/{version}/{loader_version}/{installer_version}/server/jar"

        jar_path = install_dir / "server.jar"
        download_file(server_url, jar_path)

        logger.info(f"Fabric {version} (loader {loader_version}) installed successfully")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Fabric not available for Minecraft {version}")
        else:
            logger.error(f"Failed to install Fabric: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to install Fabric: {e}")
        return False


def install_purpur(version: str, install_dir: Path) -> bool:
    """Install Purpur server (Paper fork with extra features).

    Args:
        version: Minecraft version (e.g., "1.20.4").
        install_dir: Directory to install to.

    Returns:
        True if installation was successful.
    """
    try:
        # Get latest build
        builds_url = f"{PURPUR_API}/purpur/{version}"
        response = requests.get(builds_url, timeout=TIMEOUT)
        response.raise_for_status()
        version_data = response.json()

        latest_build = version_data["builds"]["latest"]

        # Get build details for hash
        build_url = f"{PURPUR_API}/purpur/{version}/{latest_build}"
        response = requests.get(build_url, timeout=TIMEOUT)
        response.raise_for_status()
        build_data = response.json()

        _md5 = build_data.get("md5")  # Unused, kept for future verification

        # Download URL
        download_url = f"{PURPUR_API}/purpur/{version}/{latest_build}/download"

        jar_path = install_dir / "server.jar"
        download_file(download_url, jar_path)

        logger.info(f"Purpur {version} (build {latest_build}) installed successfully")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Purpur not available for Minecraft {version}")
        else:
            logger.error(f"Failed to install Purpur: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to install Purpur: {e}")
        return False


def install_server(name: str, server_type: str, version: str, install_dir: Path) -> bool:
    """Install a Minecraft server.

    Args:
        name: Server name (for logging).
        server_type: Type of server (paper, vanilla, fabric, forge, purpur).
        version: Minecraft version.
        install_dir: Directory to install to.

    Returns:
        True if installation was successful.

    Raises:
        UnsupportedServerTypeError: If the server type is not supported.
    """
    logger.info(f"Installing {server_type} {version} for server '{name}'")

    install_dir.mkdir(parents=True, exist_ok=True)

    if server_type == "paper":
        return install_paper(version, install_dir)
    elif server_type == "vanilla":
        return install_vanilla(version, install_dir)
    elif server_type == "fabric":
        return install_fabric(version, install_dir)
    elif server_type == "purpur":
        return install_purpur(version, install_dir)
    elif server_type in ("forge", "spigot"):
        # These require more complex installation (running installers)
        logger.warning(f"{server_type} installation not yet implemented")
        raise UnsupportedServerTypeError(server_type)
    else:
        raise UnsupportedServerTypeError(server_type)


def get_available_versions(server_type: str, include_snapshots: bool = False) -> list:
    """Get available versions for a server type.

    Args:
        server_type: Type of server.
        include_snapshots: Whether to include snapshot/unstable versions.

    Returns:
        List of available version strings (newest first).
    """
    try:
        if server_type == "paper":
            response = requests.get(f"{PAPER_API}/projects/paper", timeout=TIMEOUT)
            response.raise_for_status()
            versions = response.json().get("versions", [])
            # Paper versions are release versions only, return newest first
            return list(reversed(versions))

        elif server_type == "vanilla":
            response = requests.get(MOJANG_VERSION_MANIFEST, timeout=TIMEOUT)
            response.raise_for_status()
            manifest = response.json()
            if include_snapshots:
                # Return all versions (release + snapshot)
                return [v["id"] for v in manifest["versions"]]
            else:
                # Return release versions only
                return [v["id"] for v in manifest["versions"] if v["type"] == "release"]

        elif server_type == "fabric":
            response = requests.get(f"{FABRIC_META}/versions/game", timeout=TIMEOUT)
            response.raise_for_status()
            versions = response.json()
            if include_snapshots:
                return [v["version"] for v in versions]
            else:
                return [v["version"] for v in versions if v.get("stable", False)]

        elif server_type == "purpur":
            response = requests.get(f"{PURPUR_API}/purpur", timeout=TIMEOUT)
            response.raise_for_status()
            versions = response.json().get("versions", [])
            # Purpur versions are release versions only, return newest first
            return list(reversed(versions))

        else:
            return []

    except Exception as e:
        logger.error(f"Failed to fetch versions for {server_type}: {e}")
        return []


def get_server_types() -> list:
    """Get available server types with metadata.

    Returns:
        List of server type info dictionaries.
    """
    return [
        {
            "id": "paper",
            "name": "Paper",
            "description": "High performance Spigot fork with optimizations",
            "supports_snapshots": False,
        },
        {
            "id": "vanilla",
            "name": "Vanilla",
            "description": "Official Minecraft server from Mojang",
            "supports_snapshots": True,
        },
        {
            "id": "fabric",
            "name": "Fabric",
            "description": "Lightweight modding platform",
            "supports_snapshots": True,
        },
        {
            "id": "purpur",
            "name": "Purpur",
            "description": "Paper fork with extra features and configurability",
            "supports_snapshots": False,
        },
    ]
