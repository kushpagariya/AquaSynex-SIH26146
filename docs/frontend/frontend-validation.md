# Frontend Validation Rules

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Frontend validation improves UX. It is NOT the security boundary.
> Backend validation ([validation-rules.md](../backend/validation-rules.md)) is authoritative.

---

## 1. Dataset Upload Validation (Client-Side)

| Field | Rule | Error message |
|---|---|---|
| `name` | Required, 1–200 chars | "Dataset name is required" |
| `file` | Required | "Please select a file" |
| `file` extension | `.csv`, `.json`, `.jsonl`, `.parquet` | "Unsupported format. Use CSV, JSON, JSONL, or Parquet." |
| `file` size | ≤ 2GB (client estimate) | "File is too large. Maximum size is 2GB." |

## 2. Filter Input Validation

| Field | Rule |
|---|---|
| `minRiskScore` | Number, 0.0 – 1.0 |
| `maxRiskScore` | Number, 0.0 – 1.0, ≥ minRiskScore |
| `fromTimestamp` | Valid date |
| `toTimestamp` | Valid date, ≥ fromTimestamp |

## 3. Analysis Config Validation

| Field | Rule |
|---|---|
| `maxEntities` | Integer, ≥ 1 |
| `topExplanations` | Integer, 1–20 |

---

*Last updated: 2026-09-11 | Owner: Frontend Owner*
