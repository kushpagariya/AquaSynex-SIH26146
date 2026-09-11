# Agent Development Rules

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This document is specifically written for AI coding agents.**
> These are mandatory behavioral rules. Violating them will create integration failures.

---

## BEFORE CODING

### Mandatory Pre-Coding Checklist

Before writing any code for this project, the agent MUST:

**1. Read documentation first**
- [ ] Read `docs/README.md` completely
- [ ] Read the subsystem `README.md` for your assigned subsystem
- [ ] Read relevant contract documents (see agent-specific guides)
- [ ] Understand the source-of-truth hierarchy (section 5 of `docs/README.md`)

**2. Check existing patterns before creating new ones**
- [ ] Search for existing implementations of similar functionality before creating new abstractions
- [ ] Check `docs/development/naming-conventions.md` for canonical field names
- [ ] Check `docs/data/data-dictionary.md` before defining any data field
- [ ] Check `docs/backend/api-specification.md` before defining any API endpoint
- [ ] Check `docs/decisions/` for existing ADRs on the area you are working in

**3. Understand your boundaries**
- [ ] Read your subsystem's agent guide
- [ ] Know which files you own vs which you must not modify
- [ ] Know which documents define your output contracts

---

## DURING CODING

### Required Behaviors

**Field naming**
- Use ONLY canonical field names from `docs/data/data-dictionary.md` and `docs/development/naming-conventions.md`
- Do NOT invent new field names for concepts that already have canonical names
- camelCase in JSON, snake_case in Python and DuckDB

**Value representation**
- Bitcoin values: store as satoshis (integer) internally; return as 8-decimal BTC strings in API
- Timestamps: always UTC; ISO 8601 in API; `datetime` with `tzinfo=timezone.utc` in Python
- Risk scores: float in [0.0, 1.0]
- Risk levels: one of `low`, `medium`, `high`, `critical` (lowercase)

**Error handling**
- Use only error codes from `docs/backend/error-handling.md`
- Do NOT invent new error codes
- Do NOT swallow exceptions silently

**Offline compatibility**
- Do NOT call external APIs at runtime
- Do NOT use CDN resources that aren't bundled at build time
- Do NOT assume internet access during inference or analysis

**Docker compatibility**
- Use relative paths or environment variables for file paths
- Do NOT hardcode absolute paths outside of Docker container structure
- Do NOT use Windows-specific path separators (`\`) in code

**Dependencies**
- Do NOT add new Python packages to `requirements.txt` without explicitly noting it
- Do NOT add new npm packages to `package.json` without noting it
- All dependencies must be installable from PyPI/npm without internet at runtime

---

## DURING CODING — FORBIDDEN ACTIONS

| Action | Why Forbidden |
|---|---|
| Modify another subsystem's owned files without coordination | Creates conflicts and breaks contracts |
| Change a shared contract (API, ML output, graph schema) without updating documentation | Silent breaking change |
| Use a different database technology (PostgreSQL, MongoDB, Redis, etc.) | ADR-001 defines DuckDB as the only database |
| Make runtime internet calls | ADR-002 defines offline-first operation |
| Return BTC values as JSON float | Floating-point precision errors |
| Return naive (timezone-unaware) datetime objects | Inconsistent timestamp handling |
| Add authentication without an ADR | Major architectural change requires formal decision |
| Create endpoints not in `docs/backend/api-specification.md` | Undocumented APIs break the frontend contract |
| Call ML code from the frontend | Architectural violation |
| Access DuckDB from the frontend | Architectural violation |

---

## BEFORE FINISHING

### Pre-PR Verification Checklist

Before opening a Pull Request, verify:

**Contract compliance**
- [ ] Does this change break any inter-subsystem contract?
- [ ] If yes: Have you updated the relevant contract document?
- [ ] Have all affected owners been notified?

**Documentation**
- [ ] If you changed an API endpoint: Did you update `api-specification.md`?
- [ ] If you changed a DuckDB table: Did you update `duckdb-schema.md`?
- [ ] If you changed a feature: Did you update `feature-specification.md`?
- [ ] If you changed a naming convention: Did you update `naming-conventions.md`?
- [ ] If you added an environment variable: Did you update `environment-variables.md`?

**Testing**
- [ ] Do tests exist for the changed behavior?
- [ ] Do contract tests exist for changed interfaces?
- [ ] If you changed the ML output contract: Do backend tests validate the new schema?

**Deployment**
- [ ] Does the code work in a Docker container?
- [ ] Does it rely on internet access? (Must NOT)
- [ ] Does it use absolute paths that won't work in Docker? (Must NOT)
- [ ] Did you update `requirements.txt` / `package.json` if dependencies changed?

**Architecture**
- [ ] Did you introduce a new technology not in the approved stack?
  - If yes: Create an ADR in `docs/decisions/`
- [ ] Did you make a significant architectural decision not covered by existing ADRs?
  - If yes: Create an ADR

---

## WHAT TO DO IF YOU DISCOVER A BETTER ARCHITECTURE

If during implementation you discover that a technically better approach exists that differs from the documented architecture:

1. **Do NOT silently redesign the system.**
2. **Preserve the agreed architecture** in your implementation.
3. **Document the issue** — add a `DECISION REQUIRED` note in the relevant document.
4. **Create an ADR draft** in `docs/decisions/` if the change is significant.
5. **Explain the alternative** in the ADR.
6. **Leave the final decision open** for team review.

The documentation system exists to prevent incompatible architectures from being independently invented by separate agents. Preserve it.

---

## WHAT TO DO IF DOCUMENTATION IS WRONG OR OUTDATED

If you find documentation that is incorrect or outdated:

1. **Do not assume the code is wrong.** Check both code and documentation.
2. **Update the documentation** to reflect the current correct state.
3. If the documentation and code conflict: **follow the code if it's the implemented reality; update documentation to match.**
4. If the documentation is more recent than the code (e.g., a contract change was documented but not implemented): **implement to match the documentation; document any deviations.**

---

*Last updated: 2026-09-11 | Owner: All*
