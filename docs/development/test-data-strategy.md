# Test Data Strategy

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Test Data Principles

- Test data must be **synthetic or anonymized** — never include real private keys or real PII
- Test data must cover both normal and anomalous cases
- Test data must exercise all canonical fields (some required, some optional/null)
- Test data must be committed to the repository under `tests/fixtures/`

---

## 2. Synthetic Test Dataset

A small synthetic Bitcoin transaction dataset (100–1000 transactions) for:
- Unit tests
- API tests
- Contract tests
- Development without a real dataset

**Location**: `tests/fixtures/synthetic_transactions.csv`

**Required characteristics**:
- Mix of transaction counts (low/high)
- Mix of value ranges
- Some transactions with full address detail, some without
- Some transactions with timestamps, some without
- 10–15 "anomalous" entities with extreme feature values
- 85–90 "normal" entities

**Status**: `PLANNED`

---

## 3. Elliptic Dataset Reference

For integration tests and ML training validation, the Elliptic dataset is used.

**Download**: Must be downloaded manually and placed in `data/` (not committed to git — too large)

**Documentation**: See [sample-dataset-format.md](../data/sample-dataset-format.md) for format details

---

## 4. Test Fixtures

| Fixture | Location | Purpose |
|---|---|---|
| `synthetic_transactions.csv` | `tests/fixtures/` | General unit/API/contract tests |
| `synthetic_no_addresses.csv` | `tests/fixtures/` | Tests when address data is missing |
| `synthetic_with_labels.csv` | `tests/fixtures/` | Tests for supervised ML |
| `sample_ml_result.json` | `tests/fixtures/` | Mock ML output for backend tests |
| `sample_graph_export.json` | `tests/fixtures/` | Mock graph output for frontend tests |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
