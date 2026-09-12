"""Vite Proxy and Network Boundary Integration Test.

Verifies Vite dev server reverse proxy configuration, API base paths,
and FastAPI CORS headers for the frontend origin.
"""

from pathlib import Path
import re
from fastapi.testclient import TestClient
import httpx
import pytest

from backend.config import settings

VITE_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "vite.config.ts"


def test_vite_proxy_configuration_matches_backend_address():
    """Verify that frontend/vite.config.ts configures the /api reverse proxy to http://localhost:8000."""
    assert VITE_CONFIG_PATH.exists(), f"vite.config.ts not found at {VITE_CONFIG_PATH}"
    content = VITE_CONFIG_PATH.read_text(encoding="utf-8")

    # Verify server.port is 3000
    assert re.search(r"port:\s*3000", content), "Vite server port should be configured to 3000"

    # Verify /api proxy target is http://localhost:8000
    assert '"/api"' in content or "'/api'" in content, "Vite proxy must define '/api' route"
    assert re.search(r'target:\s*["\']http://localhost:8000["\']', content), (
        "Vite /api proxy target must be 'http://localhost:8000'"
    )
    assert re.search(r"changeOrigin:\s*true", content), "Vite proxy must enable changeOrigin: true"


def test_cors_headers_allow_frontend_origin(client: TestClient):
    """Verify FastAPI backend returns appropriate CORS headers for frontend dev origin."""
    frontend_origin = "http://localhost:3000"
    assert frontend_origin in settings.ALLOWED_ORIGINS, (
        f"{frontend_origin} is not in backend ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}"
    )

    # Preflight request simulation
    headers = {
        "Origin": frontend_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/datasets/upload", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == frontend_origin


def test_live_vite_proxy_if_running():
    """If the Vite frontend dev server is running on localhost:3000, probe /api/health through it."""
    try:
        resp = httpx.get("http://localhost:3000/api/health", timeout=1.0)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("success") is True
    except (httpx.ConnectError, httpx.TimeoutException):
        # Frontend dev server is not currently running; static configuration validation is verified
        pytest.skip("Vite dev server (http://localhost:3000) not running in current process; skipped live probe.")
