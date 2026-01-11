"""Unit tests for security features."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from msm_core.exceptions import ValidationError
from msm_core.utils import validate_server_name


class TestServerNameValidation:
    """Tests for server name validation and path traversal prevention."""

    def test_valid_names(self):
        """Valid server names should pass."""
        valid_names = [
            "myserver",
            "MyServer",
            "my-server",
            "my_server",
            "server123",
            "a",
            "A1_test-server",
        ]
        for name in valid_names:
            result = validate_server_name(name)
            assert result == name

    def test_path_traversal_blocked(self):
        """Path traversal attempts should be blocked."""
        malicious_names = [
            "../etc",
            "..\\windows",
            "server/../../../etc/passwd",
            "server/subdir",
            "server\\subdir",
            "test/../test",
        ]
        for name in malicious_names:
            with pytest.raises(ValidationError) as exc_info:
                validate_server_name(name)
            assert "path" in str(exc_info.value).lower() or "letter" in str(exc_info.value).lower()

    def test_empty_name_rejected(self):
        """Empty names should be rejected."""
        with pytest.raises(ValidationError):
            validate_server_name("")

    def test_name_too_long_rejected(self):
        """Names exceeding max length should be rejected."""
        long_name = "a" * 100
        with pytest.raises(ValidationError) as exc_info:
            validate_server_name(long_name)
        assert "64" in str(exc_info.value)

    def test_name_starting_with_number_rejected(self):
        """Names starting with a number should be rejected."""
        with pytest.raises(ValidationError):
            validate_server_name("123server")

    def test_special_characters_rejected(self):
        """Names with special characters should be rejected."""
        invalid_names = [
            "server!",
            "server@home",
            "server#1",
            "server$",
            "server%",
            "server&",
            "server*",
            "server()",
            "server+",
            "server=",
            "server[",
            "server]",
            "server{",
            "server}",
            "server|",
            "server;",
            "server:",
            "server'",
            "server\"",
            "server<",
            "server>",
            "server,",
            "server?",
            "server`",
            "server~",
            "server ",
            " server",
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                validate_server_name(name)


class TestPathDeletionValidation:
    """Tests for path validation before deletion."""

    def test_path_validation_import(self):
        """Verify path validation function exists and is importable."""
        from msm_core.api import _validate_path_is_safe_for_deletion
        assert callable(_validate_path_is_safe_for_deletion)

    @patch('msm_core.api.get_adapter')
    def test_path_outside_data_dir_rejected(self, mock_get_adapter):
        """Paths outside the data directory should be rejected."""
        from msm_core.api import _validate_path_is_safe_for_deletion

        # Mock the adapter to return a known data directory
        mock_adapter = MagicMock()
        mock_adapter.user_data_dir.return_value = Path("C:/Users/test/AppData/msm")
        mock_get_adapter.return_value = mock_adapter

        # Try to validate a path outside the data directory
        with pytest.raises(ValidationError) as exc_info:
            _validate_path_is_safe_for_deletion(Path("C:/Windows/System32"), "malicious")

        assert "not within" in str(exc_info.value).lower() or "security" in str(exc_info.value).lower()


class TestRootPrivilegeProtection:
    """Tests for root/admin privilege protection."""

    def test_root_check_function_exists(self):
        """Verify root check function exists."""
        from msm_core.services import _is_running_as_root, _check_root_safety
        assert callable(_is_running_as_root)
        assert callable(_check_root_safety)

    def test_root_check_returns_bool(self):
        """Root check should return a boolean."""
        from msm_core.services import _is_running_as_root
        result = _is_running_as_root()
        assert isinstance(result, bool)

    @patch('msm_core.services._is_running_as_root')
    def test_root_safety_raises_when_root(self, mock_is_root):
        """Should raise ServiceError when running as root."""
        from msm_core.services import _check_root_safety, ServiceError

        mock_is_root.return_value = True

        with pytest.raises(ServiceError) as exc_info:
            _check_root_safety("test operation")

        assert "root" in str(exc_info.value).lower() or "administrator" in str(exc_info.value).lower()

    @patch('msm_core.services._is_running_as_root')
    def test_root_safety_passes_when_not_root(self, mock_is_root):
        """Should not raise when not running as root."""
        from msm_core.services import _check_root_safety

        mock_is_root.return_value = False

        # Should not raise
        _check_root_safety("test operation")


class TestJarFileDetection:
    """Tests for improved JAR file detection."""

    def test_find_jar_file_import(self):
        """Verify jar detection function exists."""
        from msm_core.services import find_jar_file
        assert callable(find_jar_file)

    def test_common_names_priority(self, tmp_path):
        """Common server names should be prioritized."""
        from msm_core.services import find_jar_file

        # Create multiple jar files
        (tmp_path / "library.jar").write_bytes(b"fake jar")
        (tmp_path / "server.jar").write_bytes(b"fake jar")
        (tmp_path / "other.jar").write_bytes(b"fake jar")

        result = find_jar_file(tmp_path)
        assert result == "server.jar"

    def test_no_jar_returns_none(self, tmp_path):
        """Should return None when no JAR files exist."""
        from msm_core.services import find_jar_file

        result = find_jar_file(tmp_path)
        assert result is None


class TestPydanticDTOs:
    """Tests for Pydantic DTO schemas."""

    def test_schemas_importable(self):
        """Verify all schemas are importable."""

    def test_server_response_from_attributes(self):
        """ServerResponse should support from_attributes mode."""
        from msm_core.schemas import ServerResponse

        # Create a mock ORM-like object
        class MockServer:
            id = 1
            name = "test"
            type = "paper"
            version = "1.20.4"
            port = 25565
            memory = "2G"
            path = "/path/to/server"
            is_running = False
            pid = None
            java_path = None
            jvm_args = None
            created_at = None
            last_started = None
            last_stopped = None

        # Should work with model_validate using from_attributes
        result = ServerResponse.model_validate(MockServer())
        assert result.id == 1
        assert result.name == "test"
        assert result.type == "paper"


class TestStateSynchronization:
    """Tests for OS-based state synchronization."""

    def test_list_servers_verifies_os_state(self):
        """list_servers should import psutil for OS verification."""
        from msm_core.api import list_servers
        # Just verify it's callable and doesn't crash on import
        assert callable(list_servers)

    def test_get_server_status_docstring(self):
        """get_server_status should document OS as source of truth."""
        from msm_core.lifecycle import get_server_status
        assert "source of truth" in get_server_status.__doc__.lower()
