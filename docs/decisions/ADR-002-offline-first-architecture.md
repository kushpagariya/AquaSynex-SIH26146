# ADR-002: Offline-First Architecture

**Status**: ACCEPTED

**Date**: 2026-09-11

**Decision Makers**: All subsystem owners

---

## Context

SIH26146 is a forensic analysis platform for law enforcement and investigation use cases. The final demonstration must run on a machine that may have no internet connectivity. Additionally, forensic systems that call external APIs raise chain-of-custody and data security concerns.

## Decision

**The system must operate fully without internet access at runtime.**

This means:
- No calls to blockchain explorers, APIs, or CDNs at runtime
- All Python packages installed during Docker image build (before going offline)
- All npm packages bundled into the frontend build artifact
- All fonts bundled via npm (`@fontsource/inter`), not loaded from Google Fonts CDN
- ML inference runs locally using local model artifacts
- DuckDB database is a local file (no database server)

## Options Evaluated

| Approach | Problem |
|---|---|
| Online blockchain API calls | Internet dependency; chain of custody risk |
| CDN-served JavaScript/CSS | Internet dependency at runtime |
| Google Fonts from CDN | Internet dependency; blocks font rendering offline |
| **Local-only architecture** | **Selected** |

## Consequences

### Positive
- Works in secure, air-gapped forensic environments
- No data exfiltration risk (nothing sent to external APIs)
- Deterministic behavior (no dependency on external API uptime)

### Negative / Constraints
- Dataset must be pre-loaded (cannot fetch from blockchain live)
- Cannot cross-reference against real-time blockchain data
- ML models must be trained before the demonstration (cannot train online)
- Docker images must be built before going offline

## Compliance

Any code that makes an external HTTP call violates this ADR. All code must be reviewed for external dependencies before deployment.

---

*Owner: All | Status: ACCEPTED*
