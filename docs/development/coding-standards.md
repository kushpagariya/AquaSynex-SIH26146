# Coding Standards

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## Python Standards

- **Style**: PEP 8 + Black formatter
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions and classes
- **Import order**: `isort` (stdlib → third-party → local)
- **Linting**: `flake8` or `ruff`
- **Error handling**: Always use specific exception types; never `except Exception` without re-raise or logging
- **Logging**: Use `logging` module; never `print()` in production code
- **Constants**: `UPPER_SNAKE_CASE` at module level

## TypeScript / React Standards

- **Strict mode**: `"strict": true` in tsconfig.json
- **Component files**: One component per file
- **Props types**: Always define explicit TypeScript interface for props
- **No `any`**: Avoid `any` type; use `unknown` with type guards
- **Hooks**: Custom hooks in `src/hooks/`, one hook per file
- **API types**: All API response types defined in `src/types/api.ts`

## General Rules

- **No magic numbers**: Use named constants
- **No secrets in code**: Use environment variables
- **No platform-specific code** unless guarded: Code must run on both Windows (dev) and Linux (Docker)
- **Line length**: 100 chars (Python), 120 chars (TypeScript)

---

*Last updated: 2026-09-11 | Owner: All*
