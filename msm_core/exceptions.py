"""MSM Exception Hierarchy."""


class MSMError(Exception):
    """Base exception for all MSM errors."""
    pass


class ServerError(MSMError):
    """Base exception for server-related errors."""
    pass


class ServerNotFoundError(ServerError):
    """Raised when a server is not found."""
    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Server not found: {identifier}")


class ServerAlreadyExistsError(ServerError):
    """Raised when attempting to create a server that already exists."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Server already exists: {name}")


class ServerAlreadyRunningError(ServerError):
    """Raised when attempting to start an already running server."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Server is already running: {name}")


class ServerNotRunningError(ServerError):
    """Raised when attempting to stop a server that is not running."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Server is not running: {name}")


class JavaError(MSMError):
    """Base exception for Java-related errors."""
    pass


class JavaNotFoundError(JavaError):
    """Raised when Java is not found on the system."""
    def __init__(self):
        super().__init__("Java not found. Please install Java 17+ and ensure it's in your PATH.")


class JavaVersionError(JavaError):
    """Raised when Java version is incompatible."""
    def __init__(self, required: str, found: str):
        self.required = required
        self.found = found
        super().__init__(f"Java version {required} required, but found {found}")


class InstallationError(MSMError):
    """Base exception for installation errors."""
    pass


class DownloadError(InstallationError):
    """Raised when a download fails."""
    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        msg = f"Failed to download: {url}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class ChecksumError(InstallationError):
    """Raised when checksum verification fails."""
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(f"Checksum mismatch: expected {expected}, got {actual}")


class UnsupportedServerTypeError(InstallationError):
    """Raised when an unsupported server type is requested."""
    def __init__(self, server_type: str):
        self.server_type = server_type
        super().__init__(f"Unsupported server type: {server_type}")


class BackupError(MSMError):
    """Base exception for backup-related errors."""
    pass


class BackupNotFoundError(BackupError):
    """Raised when a backup is not found."""
    def __init__(self, backup_id: str):
        self.backup_id = backup_id
        super().__init__(f"Backup not found: {backup_id}")


class ConfigError(MSMError):
    """Base exception for configuration errors."""
    pass


class ValidationError(MSMError):
    """Raised when input validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error for '{field}': {message}")


class PlatformError(MSMError):
    """Raised for platform-specific errors."""
    def __init__(self, platform: str, message: str):
        self.platform = platform
        self.message = message
        super().__init__(f"[{platform}] {message}")
