# Configuration

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Configuration Strategy

All configuration is provided via **environment variables**. The backend loads settings using Pydantic's `BaseSettings`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    db_path: str = "/app/db/aquasynex.db"
    
    # Storage
    data_dir: str = "/app/data"
    models_dir: str = "/app/models"
    
    # API
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_upload_size_bytes: int = 2_147_483_648  # 2GB
    
    # ML
    default_model_id: str = "isolation_forest_v1"
    default_model_version: str = "1.0.0"
    default_top_explanations: int = 5
    default_max_entities: int = 10000
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## 2. All Environment Variables

See [environment-variables.md](../deployment/environment-variables.md) for the full reference.

---

## 3. .env.example

```bash
# Database
DB_PATH=/app/db/aquasynex.db

# Storage directories
DATA_DIR=/app/data
MODELS_DIR=/app/models

# API settings
ALLOWED_ORIGINS=http://localhost:3000
MAX_UPLOAD_SIZE_BYTES=2147483648

# ML settings
DEFAULT_MODEL_ID=isolation_forest_v1
DEFAULT_MODEL_VERSION=1.0.0
DEFAULT_TOP_EXPLANATIONS=5
DEFAULT_MAX_ENTITIES=10000

# Logging
LOG_LEVEL=INFO
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner*
*References: [environment-variables.md](../deployment/environment-variables.md)*
