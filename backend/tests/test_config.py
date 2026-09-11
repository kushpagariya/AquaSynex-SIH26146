"""Unit tests for backend configuration and settings."""

from pathlib import Path
from backend.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.DEFAULT_MODEL_ID == "isolation_forest_v1"
    assert s.DEFAULT_MODEL_VERSION == "1.0.0"
    assert s.MAX_UPLOAD_SIZE_BYTES == 2_147_483_648
    assert "http://localhost:3000" in s.ALLOWED_ORIGINS


def test_allowed_origins_parsing():
    s1 = Settings(ALLOWED_ORIGINS="http://foo.com, http://bar.com")
    assert s1.ALLOWED_ORIGINS == ["http://foo.com", "http://bar.com"]

    s2 = Settings(ALLOWED_ORIGINS='["http://foo.com", "http://baz.com"]')
    assert s2.ALLOWED_ORIGINS == ["http://foo.com", "http://baz.com"]


def test_ensure_directories(tmp_path: Path):
    db_file = tmp_path / "subdir" / "test.db"
    data_dir = tmp_path / "data"
    models_dir = tmp_path / "models"

    s = Settings(DB_PATH=str(db_file), DATA_DIR=str(data_dir), MODELS_DIR=str(models_dir))
    s.ensure_directories()

    assert db_file.parent.exists()
    assert data_dir.exists()
    assert models_dir.exists()
