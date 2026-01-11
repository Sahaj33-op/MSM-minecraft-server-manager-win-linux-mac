import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Reset the database before importing the app to ensure clean state
from msm_core.db import reset_db, DBManager


@pytest.fixture(scope="module")
def test_db():
    """Create a fresh temporary database for the test module."""
    # Create temp dir that persists for all tests in this module
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"

    # Reset and create new DB instance
    reset_db()
    from msm_core import db
    db._db_instance = DBManager(db_path)

    yield db._db_instance

    # Cleanup: dispose engine before deleting files
    if db._db_instance:
        db._db_instance.engine.dispose()
    reset_db()

    # Try to clean up temp files
    try:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def setup_test_db(test_db):
    """Ensure test database is used for each test."""
    yield


from web.backend.app import app

client = TestClient(app)


def test_read_main():
    """Test root endpoint returns HTML (frontend) or API info."""
    response = client.get("/")
    assert response.status_code == 200
    # Root may serve frontend HTML or API JSON depending on setup
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        assert "name" in data or "version" in data
    else:
        # Frontend HTML is served
        assert "text/html" in content_type or len(response.content) > 0


def test_get_servers_empty():
    response = client.get("/api/v1/servers")
    assert response.status_code == 200
    assert response.json() == []


def test_get_stats():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
