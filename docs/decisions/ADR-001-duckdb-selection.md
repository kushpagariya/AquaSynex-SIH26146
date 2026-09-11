# ADR-001: Use DuckDB as Analytical Database

**Status**: ACCEPTED

**Date**: 2026-09-11

**Decision Makers**: All subsystem owners

---

## Context

The system needs an analytical database to:
- Store canonical transaction records (potentially millions of rows)
- Execute aggregation queries (total value, counts, joins)
- Be deployable offline without a database server process
- Support Python natively

## Options Evaluated

| Option | Eliminated for |
|---|---|
| PostgreSQL | Requires server process; network dependency |
| SQLite | Poor analytical query performance; no Parquet support |
| MySQL | Requires server process; poor analytics |
| Apache Arrow / Pandas only | No persistent storage; no SQL querying |
| **DuckDB** | **Selected** |

## Decision

**Use DuckDB as the only persistent database.**

### Rationale

- **Embedded**: No separate database process. Runs in-process with FastAPI.
- **Analytical**: Column-oriented, optimized for aggregation queries common in Bitcoin forensics.
- **Offline**: Database is a local file. No network dependency.
- **Parquet-native**: `read_parquet()` allows querying large datasets without full import.
- **Python-native**: First-class Python API.
- **Transactional**: Supports ACID transactions for data consistency.

## Consequences

### Positive
- Simple deployment (no separate DB service in Docker Compose)
- No network configuration for database
- Excellent analytical query performance for our workload

### Negative / Constraints
- One writer at a time (single-user assumption holds for Phase 1)
- Not suitable for high-concurrency write workloads
- Maximum practical database size is limited by available RAM for in-memory operations

## Compliance

All backend code must use DuckDB. No other database technology may be introduced without a superseding ADR.

---

*Owner: All | Status: ACCEPTED*
