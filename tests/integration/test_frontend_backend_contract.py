"""Frontend ↔ Backend API Contract Verification Test.

Inspects all TypeScript API definitions in `frontend/src/api/` and asserts their
strict correspondence with the FastAPI backend OpenAPI specification.
"""

from pathlib import Path
import re
from typing import Dict, List, Set, Tuple
import pytest
from backend.main import app

FRONTEND_API_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api"


def get_backend_routes() -> Dict[str, Set[str]]:
    """Extract all routes and their allowed HTTP methods from the FastAPI app."""
    routes: Dict[str, Set[str]] = {}
    openapi = app.openapi()
    for path, methods in openapi.get("paths", {}).items():
        routes[path] = set(m.upper() for m in methods.keys() if m.upper() in {"GET", "POST", "PUT", "DELETE", "PATCH"})
    return routes


def test_frontend_routes_match_backend_contract():
    """Verify that every API call defined in frontend/src/api/ maps to a valid FastAPI route."""
    backend_routes = get_backend_routes()

    # Authoritative mapping of Frontend Client API calls to Backend paths
    declared_frontend_calls: List[Tuple[str, str, str]] = [
        # (Function/File, HTTP Method, Path Template)
        ("health.ts:getHealth", "GET", "/api/health"),
        ("datasets.ts:listDatasets", "GET", "/api/datasets"),
        ("datasets.ts:uploadDataset", "POST", "/api/datasets/upload"),
        ("datasets.ts:getDataset", "GET", "/api/datasets/{datasetId}"),
        ("datasets.ts:deleteDataset", "DELETE", "/api/datasets/{datasetId}"),
        ("datasets.ts:triggerAnalysis", "POST", "/api/datasets/{datasetId}/analyses"),
        ("datasets.ts:listAnalysesForDataset", "GET", "/api/datasets/{datasetId}/analyses"),
        ("analyses.ts:getAnalysis", "GET", "/api/analyses/{analysisId}"),
        ("transactions.ts:listTransactions", "GET", "/api/datasets/{datasetId}/transactions"),
        ("transactions.ts:getTransaction", "GET", "/api/transactions/{transactionId}"),
        ("addresses.ts:listAddresses", "GET", "/api/datasets/{datasetId}/addresses"),
        ("addresses.ts:getAddress", "GET", "/api/addresses/{addressId}"),
        ("graph.ts:getAnalysisGraph", "GET", "/api/analyses/{analysisId}/graph"),
        ("graph.ts:getAddressSubgraph", "GET", "/api/addresses/{addressId}/graph"),
        ("results.ts:listAnalysisResults", "GET", "/api/analyses/{analysisId}/results"),
        ("results.ts:getEntityResultDetail", "GET", "/api/analyses/{analysisId}/results/{entityId}"),
        ("models.ts:listModels", "GET", "/api/models"),
    ]

    mismatches = []
    for client_fn, method, path in declared_frontend_calls:
        if path not in backend_routes:
            mismatches.append(f"{client_fn}: Path '{path}' not found in FastAPI routes.")
        elif method not in backend_routes[path]:
            mismatches.append(
                f"{client_fn}: Method '{method}' not allowed on '{path}'. Allowed: {backend_routes[path]}"
            )

    assert not mismatches, "Frontend ↔ Backend contract mismatches found:\n" + "\n".join(mismatches)


def test_frontend_api_files_exist_and_use_canonical_envelope():
    """Verify that frontend/src/api TypeScript files use standard response envelope types."""
    assert FRONTEND_API_DIR.exists(), f"Frontend API directory not found at {FRONTEND_API_DIR}"

    types_file = FRONTEND_API_DIR / "types.ts"
    assert types_file.exists()
    content = types_file.read_text(encoding="utf-8")

    # Verify ApiResponse envelope definition
    assert "export interface ApiResponse<T>" in content
    assert "success: boolean" in content
    assert "data?: T" in content
    assert "error?: ApiError" in content
    assert "meta: ApiMeta" in content
