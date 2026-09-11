# ADR-004: Satoshi as Internal Value Representation

**Status**: ACCEPTED

**Date**: 2026-09-11

**Decision Makers**: All subsystem owners

---

## Context

Bitcoin values can be stored as:
- Floating-point (BTC): `5.00000000` → `float64`
- Integer satoshis: `500000000` → `int64` (1 BTC = 100,000,000 satoshis)

Floating-point arithmetic on BTC values can produce precision errors (e.g., `0.1 + 0.2 ≠ 0.3`), which are unacceptable in a forensic context.

## Decision

**All Bitcoin values are stored and processed internally as integer satoshis.**

BTC string representation (`"5.00000000"`) is only used in API responses for display purposes.

## Rules

| Context | Representation | Example |
|---|---|---|
| DuckDB tables | `BIGINT` satoshis | `500000000` |
| Python internal | `int` | `500000000` |
| Feature engineering | Log-transformed `float` (of satoshi value) | `log1p(500000000)` |
| API response | 8-decimal BTC string | `"5.00000000"` |
| Frontend display | 8-decimal BTC string | `"5.00000000 BTC"` |

## Consequences

### Positive
- No floating-point arithmetic errors
- Integer storage is space-efficient
- Forensically correct and auditable

### Negative / Constraints
- Requires satoshi→BTC conversion at API boundary
- Feature engineering must log-transform satoshi integers (they are large numbers)
- All developers must be aware of the convention

## Compliance

All code that stores, computes, or compares BTC values must use satoshis (integers). Float BTC values may only appear in display-only contexts.

---

*Owner: All | Status: ACCEPTED*
