# Docker Compose Reference

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> See [docker-architecture.md](./docker-architecture.md) for the full Docker service design.
> This document covers usage and configuration of Docker Compose.

---

## Commands

```bash
# Start full stack (build if needed)
docker-compose up --build

# Start in background
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild after code changes
docker-compose build backend
docker-compose up -d

# View running containers
docker-compose ps

# Execute command in container
docker-compose exec backend bash
```

---

## Environment Files

| File | Purpose |
|---|---|
| `.env` | Local overrides (not committed to git) |
| `.env.example` | Template (committed) |

Docker Compose reads `.env` automatically from the same directory as `docker-compose.yml`.

---

## Volume Management

```bash
# List volumes
docker volume ls | grep aquasynex

# Inspect a volume
docker volume inspect aquasynex-sih26146_aquasynex-db

# Remove all data (CAUTION: destroys database)
docker-compose down -v
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
