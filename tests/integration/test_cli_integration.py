import pytest
import tempfile
from pathlib import Path
from typer.testing import CliRunner

# Setup test database before importing CLI
from msm_core.db import reset_db, DBManager


@pytest.fixture(scope="module", autouse=True)
def test_db():
    """Create a fresh temporary database for CLI tests."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"

    reset_db()
    from msm_core import db
    db._db_instance = DBManager(db_path)

    yield db._db_instance

    if db._db_instance:
        db._db_instance.engine.dispose()
    reset_db()

    try:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


from cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Minecraft Server Manager" in result.stdout


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "MSM" in result.stdout


def test_info():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Platform" in result.stdout


def test_server_list():
    result = runner.invoke(app, ["server", "list"])
    # Should succeed even with empty list
    assert result.exit_code == 0


def test_server_help():
    result = runner.invoke(app, ["server", "--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "start" in result.stdout
    assert "stop" in result.stdout
