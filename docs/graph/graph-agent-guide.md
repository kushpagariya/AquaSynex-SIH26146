# Graph Agent Guide

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This guide is for the AI agent working on graph construction and analysis.
> The Graph subsystem is part of the ML Owner's responsibilities.

---

## 1. Purpose

The graph subsystem builds and analyzes the Bitcoin transaction graph to produce structural features for the ML model and topology data for the investigation dashboard.

---

## 2. Mandatory Reading

1. [`docs/README.md`](../README.md)
2. [`docs/ml/ml-agent-guide.md`](../ml/ml-agent-guide.md) — You are part of the ML subsystem
3. [`docs/graph/graph-schema.md`](./graph-schema.md) — **The graph export contract**
4. [`docs/graph/graph-construction.md`](./graph-construction.md)
5. [`docs/graph/graph-features.md`](./graph-features.md)
6. [`docs/data/canonical-schema.md`](../data/canonical-schema.md)

---

## 3. Responsibilities

- Build NetworkX DiGraph from canonical transaction data
- Enrich graph nodes with address metadata
- Compute all `PLANNED` graph features per node
- Export graph topology as JSON conforming to [graph-schema.md](./graph-schema.md)
- Produce graph feature DataFrame for ML consumption

---

## 4. Non-Responsibilities

- Data ingestion (Data Pipeline's responsibility)
- ML model training/inference (ML layer's responsibility)
- API routing (Backend's responsibility)
- DuckDB queries (except reading canonical data)
- Frontend rendering

---

## 5. Files You Own

```
pipeline/graph/
├── graph_builder.py      # NetworkX graph construction
├── graph_features.py     # Feature extraction per node
├── graph_exporter.py     # Serialize to graph-schema.md JSON format
└── graph_analysis.py     # Summary statistics
```

---

## 6. Integration Checklist

- [ ] Graph builds successfully from sample canonical dataset
- [ ] All `PLANNED` features from [graph-features.md](./graph-features.md) are computed
- [ ] Graph feature DataFrame has no NaN values (handled before ML)
- [ ] Graph export JSON matches [graph-schema.md](./graph-schema.md) exactly
- [ ] Node `id` values are Bitcoin address strings (not internal IDs)
- [ ] Edge values use satoshis (integer), BTC values are 8-decimal strings
- [ ] Graph runs without internet access
- [ ] Performance tested on 100K-transaction dataset

---

*Last updated: 2026-09-11 | Owner: ML Owner (Graph)*
