"""Java runtime management for MSM - handles Java detection, listing, and downloading."""
import logging
import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .config import get_config
from .exceptions import MSMError

logger = logging.getLogger(__name__)

# Adoptium (Eclipse Temurin) API for Java downloads
ADOPTIUM_API = "https://api.adoptium.net/v3"

# Common Java installation paths by platform
JAVA_SEARCH_PATHS = {
    "Windows": [
        Path(os.environ.get("JAVA_HOME", "")) if os.environ.get("JAVA_HOME") else None,
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Java",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Eclipse Adoptium",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Temurin",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Microsoft",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Java",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Eclipse Adoptium",
    ],
    "Linux": [
        Path(os.environ.get("JAVA_HOME", "")) if os.environ.get("JAVA_HOME") else None,
        Path("/usr/lib/jvm"),
        Path("/opt/java"),
        Path("/opt/jdk"),
        Path.home() / ".sdkman" / "candidates" / "java",
        Path.home() / ".jdks",
    ],
    "Darwin": [
        Path(os.environ.get("JAVA_HOME", "")) if os.environ.get("JAVA_HOME") else None,
        Path("/Library/Java/JavaVirtualMachines"),
        Path.home() / "Library" / "Java" / "JavaVirtualMachines",
        Path.home() / ".sdkman" / "candidates" / "java",
        Path.home() / ".jdks",
    ],
}


class JavaError(MSMError):
    """Java-related errors."""
    pass


def get_java_executable(java_home: Path) -> Optional[Path]:
    """Get the java executable path from a Java home directory.

    Args:
        java_home: Path to Java installation directory.

    Returns:
        Path to java executable or None if not found.
    """
    system = platform.system()

    if system == "Windows":
        candidates = [
            java_home / "bin" / "java.exe",
            java_home / "java.exe",
        ]
    else:
        candidates = [
            java_home / "bin" / "java",
            java_home / "java",
        ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def get_java_version(java_path: Path) -> Optional[Dict]:
    """Get version info for a Java installation.

    Args:
        java_path: Path to java executable.

    Returns:
        Dictionary with version info or None if failed.
    """
    try:
        result = subprocess.run(
            [str(java_path), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Java outputs version to stderr
        output = result.stderr or result.stdout

        # Parse version string
        lines = output.strip().split("\n")
        if not lines:
            return None

        first_line = lines[0]

        # Extract version number
        # Examples:
        # openjdk version "17.0.1" 2021-10-19
        # java version "1.8.0_291"
        version_str = None
        vendor = "Unknown"

        if '"' in first_line:
            start = first_line.index('"') + 1
            end = first_line.index('"', start)
            version_str = first_line[start:end]

        # Determine major version
        if version_str:
            if version_str.startswith("1."):
                # Old format: 1.8.0_xxx -> major version 8
                major = int(version_str.split(".")[1])
            else:
                # New format: 17.0.1 -> major version 17
                major = int(version_str.split(".")[0])
        else:
            major = 0

        # Try to determine vendor
        output_lower = output.lower()
        if "openjdk" in output_lower:
            if "temurin" in output_lower or "adoptium" in output_lower:
                vendor = "Eclipse Temurin"
            elif "corretto" in output_lower:
                vendor = "Amazon Corretto"
            elif "zulu" in output_lower:
                vendor = "Azul Zulu"
            elif "graalvm" in output_lower:
                vendor = "GraalVM"
            else:
                vendor = "OpenJDK"
        elif "hotspot" in output_lower:
            vendor = "Oracle HotSpot"

        return {
            "path": str(java_path),
            "version": version_str,
            "major_version": major,
            "vendor": vendor,
            "raw_output": output.strip(),
        }

    except Exception as e:
        logger.debug(f"Failed to get Java version from {java_path}: {e}")
        return None


def detect_installed_javas() -> List[Dict]:
    """Detect all installed Java runtimes on the system.

    Returns:
        List of dictionaries with Java installation info.
    """
    system = platform.system()
    search_paths = JAVA_SEARCH_PATHS.get(system, [])

    found_javas = []
    seen_paths = set()

    # First check PATH
    java_in_path = shutil.which("java")
    if java_in_path:
        java_path = Path(java_in_path).resolve()
        if java_path not in seen_paths:
            info = get_java_version(java_path)
            if info:
                info["source"] = "PATH"
                found_javas.append(info)
                seen_paths.add(java_path)

    # Search common installation directories
    for base_path in search_paths:
        if not base_path or not base_path.exists():
            continue

        # Check if this is a direct Java home
        java_exe = get_java_executable(base_path)
        if java_exe and java_exe.resolve() not in seen_paths:
            info = get_java_version(java_exe)
            if info:
                info["source"] = str(base_path)
                found_javas.append(info)
                seen_paths.add(java_exe.resolve())

        # Check subdirectories (e.g., /usr/lib/jvm/java-17-openjdk)
        try:
            for subdir in base_path.iterdir():
                if subdir.is_dir():
                    java_exe = get_java_executable(subdir)
                    if java_exe and java_exe.resolve() not in seen_paths:
                        info = get_java_version(java_exe)
                        if info:
                            info["source"] = str(subdir)
                            found_javas.append(info)
                            seen_paths.add(java_exe.resolve())
        except PermissionError:
            continue

    # Sort by major version descending
    found_javas.sort(key=lambda x: x.get("major_version", 0), reverse=True)

    return found_javas


def get_best_java_for_version(mc_version: str, installed_javas: Optional[List[Dict]] = None) -> Optional[Dict]:
    """Get the best Java installation for a Minecraft version.

    Minecraft version requirements:
    - 1.17+ requires Java 16+
    - 1.18+ requires Java 17+
    - 1.20.5+ requires Java 21+
    - Older versions work with Java 8+

    Args:
        mc_version: Minecraft version string (e.g., "1.20.4").
        installed_javas: Optional list of installed Javas (will detect if not provided).

    Returns:
        Best matching Java installation or None.
    """
    if installed_javas is None:
        installed_javas = detect_installed_javas()

    if not installed_javas:
        return None

    # Parse Minecraft version
    try:
        parts = mc_version.split(".")
        _mc_major = int(parts[0])  # Reserved for future use
        mc_minor = int(parts[1]) if len(parts) > 1 else 0
        mc_patch = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        # Default to requiring Java 17
        mc_minor = 20
        mc_patch = 0

    # Determine minimum Java version
    if mc_minor >= 20 and mc_patch >= 5:
        min_java = 21
    elif mc_minor >= 18:
        min_java = 17
    elif mc_minor >= 17:
        min_java = 16
    else:
        min_java = 8

    # Find best matching Java
    for java in installed_javas:
        if java.get("major_version", 0) >= min_java:
            return java

    return None


def get_available_java_versions() -> List[Dict]:
    """Get available Java versions from Adoptium API.

    Returns:
        List of available Java versions.
    """
    try:
        response = requests.get(
            f"{ADOPTIUM_API}/info/available_releases",
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        available = []
        for version in data.get("available_releases", []):
            available.append({
                "version": version,
                "lts": version in data.get("available_lts_releases", []),
            })

        return available

    except Exception as e:
        logger.error(f"Failed to get available Java versions: {e}")
        raise JavaError(f"Failed to get available Java versions: {e}")


def download_java(version: int, install_dir: Optional[Path] = None) -> Dict:
    """Download and install a Java runtime from Adoptium.

    Args:
        version: Java major version to download (e.g., 17, 21).
        install_dir: Directory to install to (default: config java_dir).

    Returns:
        Dictionary with installation info.
    """
    system = platform.system()
    arch = platform.machine().lower()

    # Map architecture names
    if arch in ("x86_64", "amd64"):
        arch = "x64"
    elif arch in ("aarch64", "arm64"):
        arch = "aarch64"
    elif arch in ("x86", "i386", "i686"):
        arch = "x86"

    # Map OS names
    os_map = {
        "Windows": "windows",
        "Linux": "linux",
        "Darwin": "mac",
    }
    os_name = os_map.get(system, "linux")

    logger.info(f"Downloading Java {version} for {os_name}/{arch}...")

    # Get download URL from Adoptium
    try:
        response = requests.get(
            f"{ADOPTIUM_API}/assets/latest/{version}/hotspot",
            params={
                "architecture": arch,
                "os": os_name,
                "image_type": "jdk",
            },
            timeout=30,
        )
        response.raise_for_status()
        assets = response.json()

        if not assets:
            raise JavaError(f"No Java {version} available for {os_name}/{arch}")

        asset = assets[0]
        binary = asset.get("binary", {})
        package = binary.get("package", {})

        download_url = package.get("link")
        filename = package.get("name")
        _checksum = package.get("checksum")  # Unused, kept for future verification

        if not download_url:
            raise JavaError("No download URL found")

    except requests.RequestException as e:
        raise JavaError(f"Failed to get download info: {e}")

    # Determine install directory
    if install_dir is None:
        config = get_config()
        install_dir = Path(config.servers_dir) / "_java"

    install_dir.mkdir(parents=True, exist_ok=True)

    # Download file
    download_path = install_dir / filename

    logger.info(f"Downloading {filename}...")
    try:
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    except Exception as e:
        if download_path.exists():
            download_path.unlink()
        raise JavaError(f"Download failed: {e}")

    # Extract archive
    logger.info(f"Extracting {filename}...")
    try:
        if filename.endswith(".zip"):
            with zipfile.ZipFile(download_path, "r") as zf:
                zf.extractall(install_dir)
        elif filename.endswith((".tar.gz", ".tgz")):
            with tarfile.open(download_path, "r:gz") as tf:
                tf.extractall(install_dir)
        else:
            raise JavaError(f"Unknown archive format: {filename}")

        # Remove archive after extraction
        download_path.unlink()

    except Exception as e:
        raise JavaError(f"Extraction failed: {e}")

    # Find the extracted Java home
    # Usually named like jdk-17.0.1+12 or similar
    java_home = None
    for item in install_dir.iterdir():
        if item.is_dir() and item.name.startswith(("jdk", "java")):
            java_exe = get_java_executable(item)
            if java_exe:
                java_home = item
                break

    if not java_home:
        raise JavaError("Could not find extracted Java installation")

    # Verify installation
    java_exe = get_java_executable(java_home)
    info = get_java_version(java_exe)

    if not info:
        raise JavaError("Installed Java does not work correctly")

    logger.info(f"Java {info['version']} installed at {java_home}")

    return {
        "java_home": str(java_home),
        "java_path": str(java_exe),
        "version": info["version"],
        "major_version": info["major_version"],
        "vendor": info["vendor"],
    }


def get_managed_javas() -> List[Dict]:
    """List Java installations managed by MSM.

    Returns:
        List of managed Java installations.
    """
    config = get_config()
    # Use data_dir from config, expand ~ to home directory
    data_dir = Path(config.data_dir).expanduser()
    java_dir = data_dir / "java"

    if not java_dir.exists():
        return []

    managed = []
    for item in java_dir.iterdir():
        if item.is_dir():
            java_exe = get_java_executable(item)
            if java_exe:
                info = get_java_version(java_exe)
                if info:
                    info["java_home"] = str(item)
                    info["managed"] = True
                    managed.append(info)

    managed.sort(key=lambda x: x.get("major_version", 0), reverse=True)
    return managed


def delete_managed_java(java_home: str) -> bool:
    """Delete a managed Java installation.

    Args:
        java_home: Path to Java home directory.

    Returns:
        True if deleted successfully.
    """
    config = get_config()
    java_dir = Path(config.servers_dir) / "_java"
    java_path = Path(java_home)

    # Safety check: only delete from managed directory
    try:
        java_path.relative_to(java_dir)
    except ValueError:
        raise JavaError("Can only delete Java installations managed by MSM")

    if not java_path.exists():
        raise JavaError(f"Java installation not found: {java_home}")

    logger.info(f"Deleting Java installation: {java_home}")
    shutil.rmtree(java_path)

    return True
