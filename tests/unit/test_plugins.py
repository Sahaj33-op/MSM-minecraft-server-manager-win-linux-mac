"""Unit tests for plugins module."""
import pytest
from unittest.mock import patch, MagicMock


class TestPluginsModule:
    """Tests for the plugins module."""

    def test_module_importable(self):
        """Verify plugins module is importable."""
        from msm_core.plugins import (
            search_modrinth,
            install_from_modrinth,
            list_plugins,
            toggle_plugin,
            check_plugin_updates,
        )
        assert callable(search_modrinth)
        assert callable(install_from_modrinth)
        assert callable(list_plugins)
        assert callable(toggle_plugin)
        assert callable(check_plugin_updates)

    def test_plugin_error_is_msm_error(self):
        """PluginError should inherit from MSMError."""
        from msm_core.plugins import PluginError
        from msm_core.exceptions import MSMError

        assert issubclass(PluginError, MSMError)


class TestPluginSearch:
    """Tests for plugin search functionality."""

    @patch('msm_core.plugins.requests.get')
    def test_search_modrinth_returns_list(self, mock_get):
        """search_modrinth should return a list of plugins."""
        from msm_core.plugins import search_modrinth

        # Mock API response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"hits": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = search_modrinth("essentials")
        assert isinstance(result, list)

    @patch('msm_core.plugins.requests.get')
    def test_search_modrinth_with_limit(self, mock_get):
        """search_modrinth should respect limit parameter."""
        from msm_core.plugins import search_modrinth

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"hits": [{"project_id": "test", "slug": "test", "title": "Test", "description": "Test", "author": "tester", "downloads": 100}] * 5}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = search_modrinth("test", limit=5)
        assert len(result) <= 5

    @patch('msm_core.plugins.requests.get')
    def test_search_hangar_returns_list(self, mock_get):
        """search_hangar should return a list of plugins."""
        from msm_core.plugins import search_hangar

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = search_hangar("vault")
        assert isinstance(result, list)


class TestPluginInstallation:
    """Tests for plugin installation."""

    @patch('msm_core.plugins.get_session')
    def test_install_server_not_found(self, mock_session):
        """Should raise PluginError for non-existent server."""
        from msm_core.plugins import install_from_modrinth, PluginError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(PluginError):
            install_from_modrinth(server_id=999, project_id="test")


class TestPluginListing:
    """Tests for plugin listing."""

    @patch('msm_core.plugins.get_session')
    def test_list_plugins_returns_list(self, mock_session):
        """list_plugins should return a list."""
        from msm_core.plugins import list_plugins

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = list_plugins(server_id=1)
        assert isinstance(result, list)


class TestPluginToggle:
    """Tests for plugin enable/disable functionality."""

    @patch('msm_core.plugins.get_session')
    def test_toggle_plugin_not_found(self, mock_session):
        """Should raise error for non-existent plugin."""
        from msm_core.plugins import toggle_plugin, PluginError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(PluginError):
            toggle_plugin(plugin_id=999, enabled=True)


class TestPluginUninstall:
    """Tests for plugin uninstallation."""

    @patch('msm_core.plugins.get_session')
    def test_uninstall_plugin_not_found(self, mock_session):
        """Should raise error for non-existent plugin."""
        from msm_core.plugins import uninstall_plugin, PluginError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(PluginError):
            uninstall_plugin(plugin_id=999)


class TestPluginUpdates:
    """Tests for plugin update checking."""

    @patch('msm_core.plugins.get_session')
    def test_check_updates_returns_list(self, mock_session):
        """check_plugin_updates should return a list."""
        from msm_core.plugins import check_plugin_updates

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        # Mock server query
        mock_server = MagicMock()
        mock_server.version = "1.20.4"
        mock_ctx.query.return_value.filter.return_value.first.return_value = mock_server
        mock_ctx.query.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = check_plugin_updates(server_id=1)
        assert isinstance(result, list)
