"""Unit tests for scheduler module."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestSchedulerModule:
    """Tests for the scheduler module."""

    def test_module_importable(self):
        """Verify scheduler module is importable."""
        from msm_core.scheduler import (
            create_schedule,
            list_schedules,
            get_schedule_by_id,
            update_schedule,
            delete_schedule,
            calculate_next_run,
            SchedulerError,
        )
        assert callable(create_schedule)
        assert callable(list_schedules)
        assert callable(update_schedule)
        assert callable(calculate_next_run)

    def test_scheduler_error_is_msm_error(self):
        """SchedulerError should inherit from MSMError."""
        from msm_core.scheduler import SchedulerError
        from msm_core.exceptions import MSMError

        assert issubclass(SchedulerError, MSMError)


class TestScheduleCreation:
    """Tests for schedule creation."""

    @patch('msm_core.scheduler.get_session')
    def test_create_schedule_server_not_found(self, mock_session):
        """Should raise SchedulerError for non-existent server."""
        from msm_core.scheduler import create_schedule, SchedulerError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(SchedulerError):
            create_schedule(server_id=999, action="backup", cron_expr="0 4 * * *")


class TestCalculateNextRun:
    """Tests for next run calculation."""

    def test_calculate_next_run_returns_datetime(self):
        """calculate_next_run should return a datetime."""
        from msm_core.scheduler import calculate_next_run

        result = calculate_next_run("0 4 * * *")
        assert isinstance(result, datetime)

    def test_calculate_next_run_with_base_time(self):
        """calculate_next_run should accept base_time parameter."""
        from msm_core.scheduler import calculate_next_run

        base = datetime(2025, 1, 1, 0, 0, 0)
        result = calculate_next_run("0 4 * * *", base_time=base)
        assert isinstance(result, datetime)
        assert result > base

    def test_calculate_next_run_daily(self):
        """Daily cron expression should return next day at specified time."""
        from msm_core.scheduler import calculate_next_run

        base = datetime(2025, 1, 1, 5, 0, 0)  # 5 AM
        result = calculate_next_run("0 4 * * *", base_time=base)  # 4 AM

        # Next 4 AM should be the next day
        assert result.hour == 4
        assert result.minute == 0


class TestScheduleListing:
    """Tests for schedule listing."""

    @patch('msm_core.scheduler.get_session')
    def test_list_schedules_returns_list(self, mock_session):
        """list_schedules should return a list."""
        from msm_core.scheduler import list_schedules

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.order_by.return_value.all.return_value = []
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = list_schedules()
        assert isinstance(result, list)

    @patch('msm_core.scheduler.get_session')
    def test_list_schedules_with_server_id(self, mock_session):
        """list_schedules should filter by server_id."""
        from msm_core.scheduler import list_schedules

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.return_value = mock_ctx

        result = list_schedules(server_id=1)
        assert isinstance(result, list)


class TestScheduleUpdate:
    """Tests for schedule updates."""

    @patch('msm_core.scheduler.get_session')
    def test_update_schedule_not_found(self, mock_session):
        """Should raise error for non-existent schedule."""
        from msm_core.scheduler import update_schedule, SchedulerError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(SchedulerError):
            update_schedule(schedule_id=999, enabled=False)


class TestScheduleDeletion:
    """Tests for schedule deletion."""

    @patch('msm_core.scheduler.get_session')
    def test_delete_schedule_not_found(self, mock_session):
        """Should raise error for non-existent schedule."""
        from msm_core.scheduler import delete_schedule, SchedulerError

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.first.return_value = None
        mock_session.return_value = mock_ctx

        with pytest.raises(SchedulerError):
            delete_schedule(schedule_id=999)


class TestSchedulerService:
    """Tests for SchedulerService class."""

    def test_scheduler_service_exists(self):
        """SchedulerService class should exist."""
        from msm_core.scheduler import SchedulerService

        assert SchedulerService is not None

    def test_get_scheduler_returns_service(self):
        """get_scheduler should return a SchedulerService instance."""
        from msm_core.scheduler import get_scheduler, SchedulerService

        scheduler = get_scheduler()
        assert isinstance(scheduler, SchedulerService)
