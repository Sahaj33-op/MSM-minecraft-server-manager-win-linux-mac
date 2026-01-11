"""Backup management for MSM."""
import logging
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .db import get_session, Server, Backup
from .config import get_config
from .exceptions import ServerNotFoundError, MSMError
from .lifecycle import stop_server, start_server

logger = logging.getLogger(__name__)


class BackupError(MSMError):
    """Backup-related errors."""
    pass


def get_backup_dir() -> Path:
    """Get the backup directory from config or default."""
    config = get_config()
    backup_dir = Path(config.servers_dir) / "_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(
    server_id: int,
    output_dir: Optional[Path] = None,
    stop_first: bool = False,
    backup_type: str = "manual",
) -> dict:
    """Create a backup of a server.

    Args:
        server_id: The server database ID.
        output_dir: Custom output directory (default: config backup dir).
        stop_first: Stop the server before backup (recommended for consistency).
        backup_type: Type of backup (manual, scheduled, pre-update).

    Returns:
        Dictionary with backup info.

    Raises:
        ServerNotFoundError: If server doesn't exist.
        BackupError: If backup fails.
    """
    with get_session() as session:
        server = session.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ServerNotFoundError(server_id)

        server_name = server.name
        server_path = Path(server.path)
        was_running = server.is_running

    if not server_path.exists():
        raise BackupError(f"Server path does not exist: {server_path}")

    # Stop server if requested and running
    if stop_first and was_running:
        logger.info(f"Stopping server '{server_name}' for backup...")
        stop_server(server_id)

    try:
        # Create backup
        backup_dir = output_dir or get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{server_name}_{timestamp}.tar.gz"
        backup_path = backup_dir / backup_name

        logger.info(f"Creating backup: {backup_path}")

        # Create tarball
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(server_path, arcname=server_name)

        # Get file size
        size_bytes = backup_path.stat().st_size

        # Record in database
        with get_session() as session:
            backup = Backup(
                server_id=server_id,
                path=str(backup_path),
                size_bytes=size_bytes,
                type=backup_type,
                status="completed",
            )
            session.add(backup)
            session.flush()
            backup_id = backup.id

        logger.info(f"Backup created: {backup_path} ({size_bytes / (1024*1024):.1f} MB)")

        return {
            "id": backup_id,
            "server_id": server_id,
            "path": str(backup_path),
            "size_bytes": size_bytes,
            "type": backup_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        # Record failed backup
        with get_session() as session:
            backup = Backup(
                server_id=server_id,
                path=str(backup_dir / f"{server_name}_failed"),
                type=backup_type,
                status="failed",
            )
            session.add(backup)

        logger.error(f"Backup failed: {e}")
        raise BackupError(f"Backup failed: {e}") from e

    finally:
        # Restart server if it was running
        if stop_first and was_running:
            logger.info(f"Restarting server '{server_name}'...")
            start_server(server_id)


def restore_backup(backup_id: int, target_path: Optional[Path] = None) -> bool:
    """Restore a server from backup.

    Args:
        backup_id: The backup database ID.
        target_path: Optional override path (default: original server path).

    Returns:
        True if restore was successful.

    Raises:
        BackupError: If restore fails.
    """
    with get_session() as session:
        backup = session.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            raise BackupError(f"Backup {backup_id} not found")

        server = session.query(Server).filter(Server.id == backup.server_id).first()
        if not server:
            raise BackupError(f"Server for backup {backup_id} not found")

        backup_path = Path(backup.path)
        restore_path = target_path or Path(server.path)
        server_name = server.name
        was_running = server.is_running
        server_id = server.id

    if not backup_path.exists():
        raise BackupError(f"Backup file not found: {backup_path}")

    # Stop server if running
    if was_running:
        logger.info(f"Stopping server '{server_name}' for restore...")
        stop_server(server_id)

    try:
        # Clear existing server directory
        if restore_path.exists():
            logger.info(f"Removing existing files at {restore_path}")
            shutil.rmtree(restore_path)

        restore_path.mkdir(parents=True, exist_ok=True)

        # Extract backup
        logger.info(f"Extracting backup to {restore_path}")
        with tarfile.open(backup_path, "r:gz") as tar:
            # Extract with proper handling
            for member in tar.getmembers():
                # Strip the server name prefix from the archive
                if member.name.startswith(server_name + "/"):
                    member.name = member.name[len(server_name) + 1:]
                elif member.name == server_name:
                    continue  # Skip the root directory entry
                tar.extract(member, restore_path)

        logger.info(f"Restore completed for server '{server_name}'")
        return True

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise BackupError(f"Restore failed: {e}") from e

    finally:
        # Restart server if it was running
        if was_running:
            logger.info(f"Restarting server '{server_name}'...")
            start_server(server_id)


def list_backups(server_id: Optional[int] = None) -> List[dict]:
    """List all backups, optionally filtered by server.

    Args:
        server_id: Optional server ID to filter by.

    Returns:
        List of backup dictionaries.
    """
    with get_session() as session:
        query = session.query(Backup)
        if server_id is not None:
            query = query.filter(Backup.server_id == server_id)

        backups = query.order_by(Backup.created_at.desc()).all()

        result = []
        for backup in backups:
            backup_path = Path(backup.path)
            exists = backup_path.exists()

            result.append({
                "id": backup.id,
                "server_id": backup.server_id,
                "path": backup.path,
                "size_bytes": backup.size_bytes,
                "created_at": backup.created_at.isoformat() if backup.created_at else None,
                "type": backup.type,
                "status": backup.status,
                "exists": exists,
            })

        return result


def delete_backup(backup_id: int, delete_file: bool = True) -> bool:
    """Delete a backup.

    Args:
        backup_id: The backup database ID.
        delete_file: Whether to delete the backup file as well.

    Returns:
        True if deletion was successful.
    """
    with get_session() as session:
        backup = session.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            raise BackupError(f"Backup {backup_id} not found")

        backup_path = Path(backup.path)

        # Delete file if requested
        if delete_file and backup_path.exists():
            logger.info(f"Deleting backup file: {backup_path}")
            backup_path.unlink()

        # Remove from database
        session.delete(backup)
        logger.info(f"Deleted backup {backup_id}")

        return True


def prune_backups(
    server_id: Optional[int] = None,
    keep_count: int = 5,
    keep_days: Optional[int] = None,
) -> int:
    """Prune old backups keeping only the most recent ones.

    Args:
        server_id: Optional server ID to prune (all if None).
        keep_count: Number of backups to keep per server.
        keep_days: Optional max age in days.

    Returns:
        Number of backups deleted.
    """
    from datetime import timedelta

    deleted = 0

    with get_session() as session:
        # Get servers to process
        if server_id is not None:
            server_ids = [server_id]
        else:
            servers = session.query(Server).all()
            server_ids = [s.id for s in servers]

        for sid in server_ids:
            backups = (
                session.query(Backup)
                .filter(Backup.server_id == sid)
                .filter(Backup.status == "completed")
                .order_by(Backup.created_at.desc())
                .all()
            )

            # Keep the most recent keep_count
            to_delete = backups[keep_count:]

            # Also filter by age if specified
            if keep_days is not None:
                cutoff = datetime.utcnow() - timedelta(days=keep_days)
                to_delete = [
                    b for b in to_delete
                    if b.created_at and b.created_at < cutoff
                ]

            for backup in to_delete:
                try:
                    backup_path = Path(backup.path)
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"Pruned backup: {backup_path}")

                    session.delete(backup)
                    deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to prune backup {backup.id}: {e}")

    logger.info(f"Pruned {deleted} backup(s)")
    return deleted


def get_backup_by_id(backup_id: int) -> Optional[dict]:
    """Get a backup by ID.

    Args:
        backup_id: The backup database ID.

    Returns:
        Backup dictionary or None.
    """
    with get_session() as session:
        backup = session.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            return None

        return {
            "id": backup.id,
            "server_id": backup.server_id,
            "path": backup.path,
            "size_bytes": backup.size_bytes,
            "created_at": backup.created_at.isoformat() if backup.created_at else None,
            "type": backup.type,
            "status": backup.status,
            "exists": Path(backup.path).exists(),
        }
