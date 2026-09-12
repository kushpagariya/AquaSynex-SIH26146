# Naming Conventions

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative naming reference.**
> One concept must have one canonical name across the project.
> All subsystems must use these conventions.

---

## 1. Layer-Specific Conventions

| Layer | Convention | Example |
|---|---|---|
| Python code | `snake_case` | `transaction_id`, `risk_score` |
| Python files | `snake_case.py` | `data_loader.py`, `model_inference.py` |
| Python classes | `PascalCase` | `DataLoader`, `MLResult`, `AnalysisService` |
| FastAPI routes | `/api/kebab-case` | `/api/datasets`, `/api/analyses` |
| JSON (API) | `camelCase` | `transactionId`, `riskScore`, `totalValueBtc` |
| React components | `PascalCase` | `RiskBadge`, `TransactionTable`, `GraphViewer` |
| React hooks | `camelCase`, `use` prefix | `useDatasets`, `useAnalysis`, `usePolling` |
| React files | `PascalCase.tsx` (components), `camelCase.ts` (utilities) | `RiskBadge.tsx`, `btcFormatter.ts` |
| TypeScript types | `PascalCase` | `DatasetSummary`, `MLResultDetail` |
| TypeScript interfaces | `PascalCase` | `ApiResponse`, `FeatureExplanation` |
| CSS/Tailwind classes | Tailwind conventions | `bg-red-600`, `text-gray-900` |
| Documentation files | `kebab-case.md` | `data-dictionary.md`, `api-specification.md` |
| Environment variables | `UPPER_SNAKE_CASE` | `DB_PATH`, `MODELS_DIR`, `LOG_LEVEL` |
| Docker services | `lowercase-hyphen` | `aquasynex-frontend`, `aquasynex-backend` |
| DuckDB tables | `snake_case` | `transactions`, `ml_results`, `analysis_runs` |
| DuckDB columns | `snake_case` | `transaction_id`, `risk_score`, `predicted_at` |
| Git branches | `kebab-case` | `ml`, `backend`, `frontend`, `data_pipeline` |

---

## 2. Canonical Field Names (Cross-Layer)

These are the ONE canonical names for each concept. All layers must use them:

| Concept | JSON/API (camelCase) | Python/DuckDB (snake_case) |
|---|---|---|
| Transaction identifier | `transactionId` | `transaction_id` |
| Block hash | `blockHash` | `block_hash` |
| Block height | `blockHeight` | `block_height` |
| Transaction timestamp | `timestamp` | `timestamp` |
| Number of inputs | `inputCount` | `input_count` |
| Number of outputs | `outputCount` | `output_count` |
| Total input value | `totalInputValueBtc` (API) | `total_input_value_satoshi` (DB) |
| Total output value | `totalOutputValueBtc` (API) | `total_output_value_satoshi` (DB) |
| Transaction fee | `feeBtc` (API) | `fee_satoshi` (DB) |
| Bitcoin address identifier | `addressId` | `address_id` |
| Entity identifier | `entityId` | `entity_id` |
| Risk score | `riskScore` | `risk_score` |
| Risk level | `riskLevel` | `risk_level` |
| Anomaly score | `anomalyScore` | `anomaly_score` |
| Dataset identifier | `datasetId` | `dataset_id` |
| Analysis identifier | `analysisId` | `analysis_id` |
| ML model identifier | `modelId` | `model_id` |
| Model version | `modelVersion` | `model_version` |
| Feature schema version | `featureSchemaVersion` | `feature_schema_version` |

**FORBIDDEN aliases** (do not use any of these):

| FORBIDDEN | Canonical replacement |
|---|---|
| `txId` / `tx_id` / `txHash` / `tx_hash` | `transactionId` / `transaction_id` |
| `walletId` / `wallet_id` | `entityId` / `entity_id` |
| `addrId` / `addr_id` / `bitcoinAddress` | `addressId` / `address_id` |
| `score` / `anomaly` (alone) | `riskScore` / `anomalyScore` |
| `level` (alone) | `riskLevel` |
| `id` (alone — creates ambiguity) | Specific: `datasetId`, `transactionId`, etc. |

---

## 3. Identifier vs Alias Rules

If two fields sound similar, they must be clearly distinguished:

| `addressId` | The Bitcoin address string — the canonical identifier for an address entity |
| `entityId` | A higher-level cluster identifier (may equal `addressId` if no clustering) |
| `transactionId` | The Bitcoin txid (64-char hex) |
| `datasetId` | System-generated UUID for a dataset |
| `analysisId` | System-generated UUID for an analysis run |

Never collapse these into a generic `id` field without qualification.

---

## 4. Enum Values

All enum values use `lowercase` in JSON:

| Enum | Values |
|---|---|
| Risk level | `low`, `medium`, `high`, `critical` |
| Dataset status | `uploaded`, `processing`, `ready`, `error` |
| Analysis status | `pending`, `running`, `completed`, `failed` |
| Entity type | `address`, `transaction` |
| Dataset format | `csv`, `json`, `jsonl`, `parquet` |
| Script type | `P2PKH`, `P2SH`, `P2WPKH`, `P2WSH`, `P2TR`, `NONSTANDARD`, `UNKNOWN` |
| SHAP direction | `increases_risk`, `decreases_risk`, `neutral` |
| Model type | `anomaly_detection`, `classification` |

---

## 5. Route Naming

API routes are `lowercase` with hyphens for multi-word resources:

```
/api/health
/api/datasets
/api/datasets/{datasetId}
/api/datasets/{datasetId}/analyses
/api/datasets/{datasetId}/transactions
/api/datasets/{datasetId}/addresses
/api/analyses/{analysisId}
/api/analyses/{analysisId}/graph
/api/analyses/{analysisId}/results
/api/analyses/{analysisId}/results/{entityId}
/api/addresses/{addressId}
/api/addresses/{addressId}/graph
/api/models
```

Route parameters use `camelCase` in the route template: `{datasetId}`, `{analysisId}`, `{addressId}`.

---

*Last updated: 2026-09-11 | Owner: All*
*References: [data-dictionary.md](../data/data-dictionary.md) | [api-specification.md](../backend/api-specification.md)*
