"""Database management for MSM."""
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Server(Base):
    """Minecraft server model."""
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50))  # paper, fabric, vanilla, forge
    version: Mapped[str] = mapped_column(String(50))
    path: Mapped[str] = mapped_column(Text)
    port: Mapped[int] = mapped_column(Integer, default=25565)
    memory: Mapped[str] = mapped_column(String(20), default="2G")
    java_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jvm_args: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Runtime state (reconciled on startup)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_started: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_stopped: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        status = "running" if self.is_running else "stopped"
        return f"<Server(name='{self.name}', type='{self.type}', version='{self.version}', {status})>"


class Backup(Base):
    """Server backup model."""
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(Integer, index=True)
    path: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    type: Mapped[str] = mapped_column(String(20), default="manual")  # manual, scheduled, pre-update
    status: Mapped[str] = mapped_column(String(20), default="completed")  # in_progress, completed, failed

    def __repr__(self) -> str:
        return f"<Backup(server_id={self.server_id}, type='{self.type}', status='{self.status}')>"


class DBManager:
    """Manages database connections and sessions."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Lazy import to avoid circular dependency
            from platform_adapters import get_adapter
            adapter = get_adapter()
            data_dir = adapter.user_data_dir("msm")
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "msm.db"

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            pool_pre_ping=True
        )
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine)
        logger.debug(f"Database initialized at {db_path}")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.

        Usage:
            with db.session() as session:
                server = session.query(Server).first()
                server.is_running = True
                # Automatically commits on success, rolls back on exception
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a raw session. Caller is responsible for closing.

        Prefer using the `session()` context manager instead.
        """
        return self._session_factory()


# Lazy singleton pattern
_db_instance: Optional[DBManager] = None


def get_db() -> DBManager:
    """Get the global database manager instance (lazy initialization)."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DBManager()
    return _db_instance


def reset_db() -> None:
    """Reset the global database instance. Useful for testing."""
    global _db_instance
    _db_instance = None


# Convenience function for common pattern
@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session with automatic commit/rollback.

    Usage:
        from msm_core.db import get_session, Server

        with get_session() as session:
            servers = session.query(Server).all()
    """
    with get_db().session() as session:
        yield session
