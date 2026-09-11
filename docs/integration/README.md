# Integration Overview

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## Data Flow Integration Map

```
[Investigator uploads dataset file via browser]
    │
    ▼
[Frontend] POST /api/datasets/upload
    │
    ▼
[Backend] stores file, creates dataset record, status='uploaded'
    │
    ▼
[Backend] triggers data pipeline (background task)
    │
    ▼
[Pipeline: Data] load → validate → normalize → write canonical records to DuckDB
    │
    ▼
[Backend] updates dataset status to 'ready'
    │
    ▼
[Frontend] polls dataset status; shows 'ready'
[Investigator clicks Analyze]
    │
    ▼
[Frontend] POST /api/datasets/{id}/analyses
    │
    ▼
[Backend] creates analysis_run record, status='pending', returns analysisId
[Backend] starts background analysis task
    │
    ▼
[Pipeline: Graph] reads canonical data → builds NetworkX DiGraph → extracts graph features
    │
    ▼
[Pipeline: ML] reads canonical data + graph features → feature engineering → model inference
    │
    ▼
[Pipeline: ML] produces MLResult objects → returns to backend
    │
    ▼
[Backend] persists MLResults to ml_results table → updates analysis_run status='completed'
    │
    ▼
[Frontend] poll detects 'completed' → navigates to results view
    │
    ▼
[Investigator] browses transactions, addresses, risk scores, graph
[Investigator] clicks on high-risk address
    │
    ▼
[Frontend] GET /api/addresses/{addressId}
           GET /api/addresses/{addressId}/graph
    │
    ▼
[Frontend] renders address profile + graph neighborhood + SHAP explanation cards
```

---

## Integration Documents

| Document | Purpose |
|---|---|
| [data-pipeline-integration.md](./data-pipeline-integration.md) | How the data pipeline hands off to the backend |
| [ml-backend-integration.md](./ml-backend-integration.md) | How ML output is consumed by the backend |
| [backend-frontend-integration.md](./backend-frontend-integration.md) | How the frontend consumes the backend API |
| [end-to-end-scenarios.md](./end-to-end-scenarios.md) | Test scenarios spanning all subsystems |

---

*Last updated: 2026-09-11 | Owner: All*
