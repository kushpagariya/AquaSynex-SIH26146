# ADR-003: Use NetworkX for Graph Construction (In-Memory, No Graph Database)

**Status**: ACCEPTED

**Date**: 2026-09-11

**Decision Makers**: All subsystem owners

---

## Context

The system needs to build and analyze a Bitcoin transaction graph. Options include:
- Graph database (Neo4j, Amazon Neptune)
- In-memory graph library (NetworkX, igraph)
- Custom adjacency list in DuckDB

## Decision

**Use Python NetworkX for in-memory graph construction per analysis run.**

## Rationale

- **No separate service**: Consistent with the offline, no-external-services architecture
- **Python-native**: Integrates directly with the ML pipeline (sklearn, SHAP)
- **Algorithm breadth**: Provides PageRank, connected components, betweenness centrality out of the box
- **Sufficient scale**: For expected dataset sizes (up to ~1M transactions), NetworkX is feasible

## Alternatives Evaluated

| Option | Eliminated for |
|---|---|
| Neo4j | Requires separate service; Java dependency; complex offline setup |
| igraph | Less community support; C dependency for Python bindings |
| DuckDB adjacency list | No native graph algorithms; must implement manually |
| **NetworkX** | **Selected** |

## Consequences

### Positive
- No additional services in Docker Compose
- Direct Python integration with ML pipeline
- Rich algorithm library

### Negative / Constraints
- Memory-bound: Very large graphs (>5M nodes) may require sampling
- Not persistent: Graph rebuilt per analysis run (no incremental update)
- Single-threaded: NetworkX algorithms run in Python; no parallel execution

## Future Consideration

If graph scale becomes a bottleneck, consider:
- Subgraph sampling strategies
- Switching to `igraph` (faster C library)
- Introducing a lightweight embedded graph store

A new ADR would be required before any such change.

---

*Owner: ML Owner | Status: ACCEPTED*
