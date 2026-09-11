# Testing Strategy

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Testing Pyramid

```
                    ┌─────────────────┐
                    │  End-to-End     │   (few, expensive)
                    │  Tests          │
                  ┌─┴─────────────────┴─┐
                  │  Integration Tests  │
                ┌─┴─────────────────────┴─┐
                │   Contract Tests         │
              ┌─┴─────────────────────────┴─┐
              │   API Tests                  │
            ┌─┴─────────────────────────────┴─┐
            │   ML / Graph Tests               │
          ┌─┴─────────────────────────────────┴─┐
          │   Unit Tests (many, fast)             │
          └───────────────────────────────────────┘
```

---

## 2. Unit Tests

### ML / Data Pipeline

**What to test**:
- Field normalization logic (BTC → satoshis, timestamp parsing, null handling)
- Feature engineering functions (each feature formula)
- Risk score computation (given anomaly score → expected risk level)
- SHAP explanation structuring (given SHAP values → expected FeatureExplanation objects)
- Validation error detection (missing fields, out-of-range values)

**Framework**: `pytest`

**Location**: `tests/unit/pipeline/`

---

### Backend

**What to test**:
- Pydantic schema validation (valid/invalid inputs)
- BTC/satoshi conversion utilities
- Pagination parameter handling
- Error mapping (exception → error code)
- DuckDB query construction

**Framework**: `pytest`

**Location**: `tests/unit/backend/`

---

### Frontend

**What to test**:
- `btcFormatter.ts` utility functions
- `dateFormatter.ts` utility functions
- Risk level color mapping
- API client error handling

**Framework**: `vitest` + `@testing-library/react`

**Location**: `frontend/src/__tests__/`

---

## 3. API Tests

**What to test**:
- Each endpoint returns correct HTTP status codes
- Response envelope shape (`success`, `data`, `meta`)
- Error responses match error contract
- Pagination metadata is accurate
- BTC values are 8-decimal strings (not floats)
- Timestamps are UTC ISO 8601

**Framework**: `pytest` + `httpx` (FastAPI TestClient)

**Location**: `tests/api/`

---

## 4. Contract Tests

**Critical test category.** These verify that inter-subsystem contracts are honored.

### ML Output → Backend

```python
def test_ml_result_schema_compliance():
    """ML output must conform to model-output-contract.md"""
    results = run_analysis(dataset_id=TEST_DATASET_ID, ...)
    for result in results:
        assert 0.0 <= result.prediction.risk_score <= 1.0
        assert result.prediction.risk_level in ['low', 'medium', 'high', 'critical']
        assert result.model.model_id is not None
        for explanation in result.explanations:
            assert explanation.feature_name in CANONICAL_FEATURE_NAMES
            assert explanation.direction in ['increases_risk', 'decreases_risk', 'neutral']
```

### Backend API → Frontend

```python
def test_api_response_schema():
    """API responses must conform to frontend-backend-contract.md"""
    response = client.get("/api/datasets")
    assert response.json()["success"] is True
    for dataset in response.json()["data"]:
        assert "datasetId" in dataset
        assert "status" in dataset
        # BTC fields must be strings
        # Risk score fields must be float or null
```

### Data Pipeline → Canonical Schema

```python
def test_canonical_schema_compliance():
    """Canonical records must match canonical-schema.md"""
    run_pipeline(TEST_RAW_FILE)
    records = db.execute("SELECT * FROM transactions LIMIT 10").fetchdf()
    assert "transaction_id" in records.columns
    assert records["fee_satoshi"].dtype in [int, "Int64"]
    # No float BTC values in database
```

**Location**: `tests/contracts/`

---

## 5. ML-Specific Tests

- Feature engineering produces expected columns (from feature-specification.md)
- No NaN values in feature matrix before model input
- Model loads from artifact without error
- Anomaly scores are in [0.0, 1.0]
- Risk levels are consistent with risk scores
- SHAP values sum to approximately (predicted_value - expected_value)

**Location**: `tests/ml/`

---

## 6. Graph Tests

- Graph builds from sample canonical data without error
- Node count ≤ distinct address count
- Edge direction is correct (input → output)
- Graph features match expected values for known test graph
- Graph export JSON matches graph-schema.md

**Location**: `tests/graph/`

---

## 7. Integration Tests

**End-to-end pipeline test** (without UI):

```
Upload dataset file
    │
    ▼
Data pipeline runs → canonical records in DuckDB
    │
    ▼
Graph builds → graph features computed
    │
    ▼
ML runs → MLResult objects produced
    │
    ▼
Results stored in DuckDB
    │
    ▼
API returns results → verify schema compliance
```

**Location**: `tests/integration/`

**Requirements**: Docker Compose running, test dataset file available.

---

## 8. End-to-End Tests (PLANNED)

Full UI-driven test using a browser automation framework.

**Framework**: `playwright` (PLANNED)

**Test scenarios**:
1. Upload CSV dataset → wait for processing → verify transaction count
2. Trigger analysis → wait for completion → verify risk scores appear
3. Filter transactions by risk level → verify filtered results
4. Click address → verify detail page loads with explanations
5. Open graph → verify nodes appear colored by risk level

**Location**: `tests/e2e/`

**Status**: `PLANNED` — requires full Docker stack to be running

---

## 9. Test Data

See [test-data-strategy.md](./test-data-strategy.md) for how test datasets are created and managed.

---

## 10. Testing Commands

```bash
# Unit tests
pytest tests/unit/ -v

# API tests
pytest tests/api/ -v

# Contract tests
pytest tests/contracts/ -v

# ML tests
pytest tests/ml/ -v

# All backend tests
pytest tests/ -v --ignore=tests/e2e

# Frontend tests
cd frontend && npm test

# E2E tests (requires Docker stack)
pytest tests/e2e/ -v
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
