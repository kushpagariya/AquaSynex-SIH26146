# Offline Deployment

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **HARD REQUIREMENT**: The system must function without internet access at runtime.

---

## 1. Offline Requirement Statement

The final SIH demonstration must be capable of running on a machine with no internet connectivity. This is a hard architectural constraint. See [ADR-002](../decisions/ADR-002-offline-first-architecture.md).

---

## 2. What Must Be Available Locally at Demonstration Time

| Resource | How it gets offline | Who prepares it |
|---|---|---|
| Docker images | Built before going offline; saved as `.tar` archives | All owners |
| Python packages | Installed during Docker image build | Backend / ML Owner |
| npm packages + frontend build | Bundled during Docker image build | Frontend Owner |
| Trained ML model artifacts | Placed in `/models/` volume before demonstration | ML Owner |
| Dataset file(s) | Provided by investigator; uploaded via UI | ML Owner / Operator |
| Google Fonts | Downloaded via `@fontsource/inter` npm package during build | Frontend Owner |
| DuckDB database | Created fresh on first run (empty, built by pipeline) | Backend Owner |

---

## 3. Pre-Offline Build Procedure

Before the event with internet access:

```bash
# 1. Build Docker images
docker-compose build

# 2. Save images to tar archives (for transport to offline machine)
docker save aquasynex-backend:latest -o aquasynex-backend.tar
docker save aquasynex-frontend:latest -o aquasynex-frontend.tar

# 3. Copy to offline machine or USB drive
cp aquasynex-backend.tar aquasynex-frontend.tar /path/to/usb/

# 4. Copy trained model artifacts
cp -r models/ /path/to/usb/
```

---

## 4. Offline Machine Setup Procedure

```bash
# 1. Load Docker images
docker load -i aquasynex-backend.tar
docker load -i aquasynex-frontend.tar

# 2. Copy model artifacts to models volume location
# (Exact path depends on Docker volume configuration)

# 3. Start the stack
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/api/health

# 5. Access the application
# Open browser to http://localhost:3000
```

---

## 5. Runtime Internet Prohibition Checklist

All subsystem owners must verify:

- [ ] Backend: No requests to external APIs (blockchain explorers, etc.)
- [ ] Backend: All Python packages installed during image build
- [ ] ML: Model inference loads from local artifact file
- [ ] ML: SHAP computation is local
- [ ] Frontend: All JavaScript bundles served from Nginx (no CDN)
- [ ] Frontend: Fonts loaded from npm package (not Google Fonts CDN)
- [ ] Frontend: API calls only go to `http://localhost:3000/api` (Nginx proxy → local backend)
- [ ] Docker Compose: No `build:` sections that require internet at runtime

---

## 6. Dataset Preparation for Demo

The demonstration dataset must be:
1. Pre-processed and available as a CSV or Parquet file on the demo machine
2. Loaded via the web UI before the demonstration begins
3. Analysis must complete before the demonstration

Allow ~5–15 minutes for dataset upload and analysis on the demonstration machine.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
*References: [ADR-002](../decisions/ADR-002-offline-first-architecture.md) | [deployment-checklist.md](./deployment-checklist.md)*
