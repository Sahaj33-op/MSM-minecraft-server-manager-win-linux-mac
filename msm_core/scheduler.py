"""Scheduler service for MSM - handles scheduled tasks."""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from croniter import croniter

from .db import get_session, Server, Base
from .exceptions import MSMError
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger(__name__)


class Schedule(Base):
    """Scheduled task model."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(50))  # backup, restart, stop, start, command
    cron: Mapped[str] = mapped_column(String(100))  # "0 4 * * *" = 4am daily
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON for additional args
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Schedule(server_id={self.server_id}, action='{self.action}', cron='{self.cron}')>"


class SchedulerError(MSMError):
    """Scheduler-related errors."""
    pass


def calculate_next_run(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate the next run time for a cron expression.

    Args:
        cron_expr: Cron expression (e.g., "0 4 * * *").
        base_time: Base time to calculate from (default: now).

    Returns:
        Next run datetime.
    """
    base = base_time or datetime.now()
    cron = croniter(cron_expr, base)
    return cron.get_next(datetime)


def create_schedule(
    server_id: int,
    action: str,
    cron_expr: str,
    payload: Optional[str] = None,
    enabled: bool = True,
) -> dict:
    """Create a new scheduled task.

    Args:
        server_id: The server database ID.
        action: Action to perform (backup, restart, stop, start, command).
        cron_expr: Cron expression for scheduling.
        payload: Optional JSON payload for the action.
        enabled: Whether the schedule is enabled.

    Returns:
        Dictionary with schedule info.
    """
    # Validate cron expression
    try:
        croniter(cron_expr)
    except Exception as e:
        raise SchedulerError(f"Invalid cron expression: {e}")

    # Validate action
    valid_actions = ["backup", "restart", "stop", "start", "command"]
    if action not in valid_actions:
        raise SchedulerError(f"Invalid action. Must be one of: {valid_actions}")

    next_run = calculate_next_run(cron_expr) if enabled else None

    with get_session() as session:
        # Verify server exists
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise SchedulerError(f"Server {server_id} not found")

        schedule = Schedule(
            server_id=server_id,
            action=action,
            cron=cron_expr,
            enabled=enabled,
            next_run=next_run,
            payload=payload,
        )
        session.add(schedule)
        session.flush()

        return {
            "id": schedule.id,
            "server_id": schedule.server_id,
            "action": schedule.action,
            "cron": schedule.cron,
            "enabled": schedule.enabled,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "payload": schedule.payload,
        }


def update_schedule(
    schedule_id: int,
    cron_expr: Optional[str] = None,
    enabled: Optional[bool] = None,
    payload: Optional[str] = None,
) -> dict:
    """Update a scheduled task.

    Args:
        schedule_id: The schedule database ID.
        cron_expr: New cron expression.
        enabled: Enable/disable the schedule.
        payload: New payload.

    Returns:
        Updated schedule dictionary.
    """
    with get_session() as session:
        schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise SchedulerError(f"Schedule {schedule_id} not found")

        if cron_expr is not None:
            try:
                croniter(cron_expr)
            except Exception as e:
                raise SchedulerError(f"Invalid cron expression: {e}")
            schedule.cron = cron_expr

        if enabled is not None:
            schedule.enabled = enabled

        if payload is not None:
            schedule.payload = payload

        # Recalculate next run
        if schedule.enabled:
            schedule.next_run = calculate_next_run(schedule.cron)
        else:
            schedule.next_run = None

        return {
            "id": schedule.id,
            "server_id": schedule.server_id,
            "action": schedule.action,
            "cron": schedule.cron,
            "enabled": schedule.enabled,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "payload": schedule.payload,
        }


def delete_schedule(schedule_id: int) -> bool:
    """Delete a scheduled task.

    Args:
        schedule_id: The schedule database ID.

    Returns:
        True if deleted successfully.
    """
    with get_session() as session:
        schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise SchedulerError(f"Schedule {schedule_id} not found")

        session.delete(schedule)
        logger.info(f"Deleted schedule {schedule_id}")
        return True


def list_schedules(server_id: Optional[int] = None) -> List[dict]:
    """List all schedules, optionally filtered by server.

    Args:
        server_id: Optional server ID to filter by.

    Returns:
        List of schedule dictionaries.
    """
    with get_session() as session:
        query = session.query(Schedule)
        if server_id is not None:
            query = query.filter(Schedule.server_id == server_id)

        schedules = query.order_by(Schedule.next_run).all()

        return [
            {
                "id": s.id,
                "server_id": s.server_id,
                "action": s.action,
                "cron": s.cron,
                "enabled": s.enabled,
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "next_run": s.next_run.isoformat() if s.next_run else None,
                "payload": s.payload,
            }
            for s in schedules
        ]


def get_schedule_by_id(schedule_id: int) -> Optional[dict]:
    """Get a schedule by ID.

    Args:
        schedule_id: The schedule database ID.

    Returns:
        Schedule dictionary or None.
    """
    with get_session() as session:
        schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return None

        return {
            "id": schedule.id,
            "server_id": schedule.server_id,
            "action": schedule.action,
            "cron": schedule.cron,
            "enabled": schedule.enabled,
            "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "payload": schedule.payload,
        }


class SchedulerService:
    """Background service that runs scheduled tasks."""

    _instance: Optional["SchedulerService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SchedulerService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 60  # Check every minute
        self._action_handlers: Dict[str, Callable] = {}
        self._initialized = True

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default action handlers."""
        from . import lifecycle, backups

        self._action_handlers = {
            "start": lambda server_id, _: lifecycle.start_server(server_id),
            "stop": lambda server_id, _: lifecycle.stop_server(server_id),
            "restart": lambda server_id, _: lifecycle.restart_server(server_id),
            "backup": lambda server_id, _: backups.create_backup(server_id, backup_type="scheduled"),
            "command": self._handle_command,
        }

    def _handle_command(self, server_id: int, payload: Optional[str]) -> bool:
        """Handle command action."""
        from . import lifecycle
        import json

        if not payload:
            logger.warning("Command action requires payload")
            return False

        try:
            data = json.loads(payload)
            command = data.get("command", "")
            if command:
                return lifecycle.send_command(server_id, command)
        except json.JSONDecodeError:
            # Treat payload as raw command
            return lifecycle.send_command(server_id, payload)

        return False

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register a custom action handler.

        Args:
            action: Action name.
            handler: Function(server_id, payload) -> bool.
        """
        self._action_handlers[action] = handler

    def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler service started")

    def stop(self) -> None:
        """Stop the scheduler service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Scheduler service stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                self._check_and_run_schedules()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            time.sleep(self._check_interval)

    def _check_and_run_schedules(self) -> None:
        """Check for due schedules and run them."""
        now = datetime.now()

        with get_session() as session:
            due_schedules = (
                session.query(Schedule)
                .filter(Schedule.enabled == True)
                .filter(Schedule.next_run <= now)
                .all()
            )

            for schedule in due_schedules:
                self._execute_schedule(schedule)

                # Update schedule
                schedule.last_run = now
                schedule.next_run = calculate_next_run(schedule.cron, now)

    def _execute_schedule(self, schedule: Schedule) -> None:
        """Execute a scheduled task."""
        logger.info(f"Executing schedule {schedule.id}: {schedule.action} for server {schedule.server_id}")

        handler = self._action_handlers.get(schedule.action)
        if not handler:
            logger.warning(f"No handler for action: {schedule.action}")
            return

        try:
            handler(schedule.server_id, schedule.payload)
            logger.info(f"Schedule {schedule.id} executed successfully")
        except Exception as e:
            logger.error(f"Schedule {schedule.id} failed: {e}")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


def get_scheduler() -> SchedulerService:
    """Get the singleton scheduler instance."""
    return SchedulerService()
