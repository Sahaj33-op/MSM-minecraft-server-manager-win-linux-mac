"""Unit tests for backups module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestBackupsModule:
    """Tests for the backups module."""

    def test_module_importable(self):
        """Verify backups module is importable."""
        from msm_core.backups import (
            create_backup,
            list_backups,
            restore_backup,
        )
        assert callable(create_backup)
        assert callable(list_backups)
        assert callable(restore_backup)

    def test_backup_error_is_msm_error(self):
        """BackupError should inherit from MSMError."""
        from msm_core.backups import BackupError
        from msm_core.exceptions import MSMError

        assert issubclass(BackupError, MSMError)

    def test_get_backup_dir(self):
        """get_backup_dir should return a Path."""
        from msm_core.backups import get_backup_dir

        result = get_backup_dir()
        assert isinstance(result, Path)


class TestBackupCreation:
    """Tests for backup creation."""

    @patch('msm_core.backups.get_session')
    def test_create_backup_server_not_found(self, mock_session):
        """Should raise ServerNotFoundError for non-existent server."""
        from msm_core.backups import create_backup
        from msm_core.exceptions import ServerNotFoundError

        # Mock session to return no server
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(ServerNotFoundError):
            create_backup(server_id=999)


class TestBackupListing:
    """Tests for backup listing."""

    @patch('msm_core.backups.get_session')
    def test_list_backups_returns_list(self, mock_session):
        """list_backups should return a list."""
        from msm_core.backups import list_backups

        # Mock session
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.order_by.return_value.all.return_value = []
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = list_backups()
        assert isinstance(result, list)

    @patch('msm_core.backups.get_session')
    def test_list_backups_with_server_id(self, mock_session):
        """list_backups should filter by server_id when provided."""
        from msm_core.backups import list_backups

        # Mock session
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_ctx.query.return_value = mock_query
        mock_session.return_value = mock_ctx

        result = list_backups(server_id=1)
        assert isinstance(result, list)


class TestBackupDeletion:
    """Tests for backup deletion."""

    @patch('msm_core.backups.get_session')
    def test_delete_backup_not_found(self, mock_session):
        """Should raise error for non-existent backup."""
        from msm_core.backups import delete_backup, BackupError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(BackupError):
            delete_backup(backup_id=999)


class TestBackupPruning:
    """Tests for backup pruning."""

    @patch('msm_core.backups.get_session')
    @patch('msm_core.backups.delete_backup')
    def test_prune_backups_returns_count(self, mock_delete, mock_session):
        """prune_backups should return count of deleted backups."""
        from msm_core.backups import prune_backups

        # Mock session to return empty list
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_ctx.query.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = prune_backups(keep_count=5)
        assert isinstance(result, int)
        assert result >= 0
