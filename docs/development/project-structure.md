# Project Structure

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Status labels: `IMPLEMENTED`, `IN PROGRESS`, `PLANNED`, `PLACEHOLDER`, `FUTURE`

---

## Expected Repository Layout

```
AquaSynex-SIH26146/
│
├── README.md                          ← Root README                [IN PROGRESS]
├── .gitignore                         ← Git ignore file            [PLANNED]
├── docker-compose.yml                 ← Docker orchestration       [PLANNED]
│
├── docs/                              ← All documentation          [IN PROGRESS]
│   ├── README.md                      ← Documentation index        [IMPLEMENTED]
│   ├── architecture/                                               [IMPLEMENTED]
│   ├── data/                                                       [IMPLEMENTED]
│   ├── ml/                                                         [IMPLEMENTED]
│   ├── graph/                                                       [IMPLEMENTED]
│   ├── backend/                                                     [IMPLEMENTED]
│   ├── frontend/                                                   [IMPLEMENTED]
│   ├── integration/                                                [IMPLEMENTED]
│   ├── development/                                                [IMPLEMENTED]
│   ├── deployment/                                                 [IMPLEMENTED]
│   └── decisions/                                                  [IMPLEMENTED]
│
├── backend/                           ← FastAPI backend            [PLANNED]
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── services/
│   ├── db/
│   ├── schemas/
│   └── utils/
│
├── frontend/                          ← React + Vite frontend      [PLANNED]
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── store/
│       ├── types/
│       └── utils/
│
├── pipeline/                          ← ML / Data / Graph code     [PLANNED]
│   ├── requirements.txt
│   ├── data/
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── normalizer.py
│   │   └── duckdb_writer.py
│   ├── graph/
│   │   ├── graph_builder.py
│   │   ├── graph_features.py
│   │   └── graph_exporter.py
│   └── ml/
│       ├── feature_engineering.py
│       ├── model_trainer.py
│       ├── model_inference.py
│       ├── risk_scorer.py
│       ├── explainer.py
│       └── result_builder.py
│
├── models/                            ← Trained ML model artifacts [PLANNED]
│   └── isolation_forest_v1/
│       └── 1.0.0/
│           ├── model.pkl
│           ├── scaler.pkl
│           ├── model_metadata.json
│           └── evaluation_report.json
│
├── data/                              ← Dataset storage (gitignored) [PLANNED]
│   └── .gitkeep
│
├── tests/                             ← Test suite                 [PLANNED]
│   ├── unit/
│   ├── api/
│   ├── contracts/
│   ├── ml/
│   ├── graph/
│   ├── integration/
│   └── e2e/
│
└── scripts/                           ← Utility scripts            [PLANNED]
    ├── setup_dev.sh
    └── build_offline.sh
```

---

## Key File Ownership

| Path | Owner |
|---|---|
| `backend/` | Backend Owner |
| `frontend/` | Frontend Owner |
| `pipeline/` | ML Owner |
| `models/` | ML Owner (creates), Backend Owner (reads) |
| `data/` | ML Owner (writes), Backend Owner (reads via DuckDB) |
| `docs/` | All owners (respective subsystem docs) |
| `docker-compose.yml` | All owners (integration) |
| `tests/contracts/` | All owners |
| `tests/integration/` | All owners |
| `tests/e2e/` | All owners |

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: All*
