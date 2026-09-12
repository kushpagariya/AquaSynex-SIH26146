"""Application configuration module for AquaSynex Backend.

Loads environment variables via Pydantic BaseSettings, providing sensible defaults
and portable path resolution for local dev, testing, and Docker environments.
"""

from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    # Defaults to a local directory if in dev, or /app/db in Docker
    DB_PATH: str = str(BASE_DIR / "data" / "aquasynex.db")

    # Storage directories
    DATA_DIR: str = str(BASE_DIR / "data")
    MODELS_DIR: str = str(BASE_DIR / "models")

    # API Settings
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    MAX_UPLOAD_SIZE_BYTES: int = 2_147_483_648  # 2 GB

    # ML Settings
    DEFAULT_MODEL_ID: str = "isolation_forest_v1"
    DEFAULT_MODEL_VERSION: str = "1.0.0"
    DEFAULT_TOP_EXPLANATIONS: int = 5
    DEFAULT_MAX_ENTITIES: int = 10000

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=(".env", str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # JSON string
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def ensure_directories(self) -> None:
        """Ensure runtime directories exist."""
        db_path = Path(self.DB_PATH)
        if db_path.name != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.MODELS_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
