# Linux Deployment

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Target Platform

- **OS**: Ubuntu 22.04 LTS (recommended)
- **Architecture**: x86_64
- **RAM**: Minimum 8GB (16GB recommended for large datasets)
- **Storage**: Minimum 20GB free (for Docker images, data, and models)

---

## 2. Prerequisites

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose Plugin
sudo apt-get install docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

## 3. Deployment Steps

```bash
# 1. Clone repository (or transfer files to machine)
git clone <repo-url> AquaSynex-SIH26146
cd AquaSynex-SIH26146

# 2. Copy environment file
cp .env.example .env
# Edit .env if needed

# 3. Build and start
docker compose up --build -d

# 4. Verify health
curl http://localhost:8000/api/health

# 5. Open browser
# Navigate to http://localhost:3000
```

---

## 4. Port Mapping

| Port | Service | Access |
|---|---|---|
| `3000` | Frontend (Nginx) | Open to LAN/demo audience |
| `8000` | Backend (FastAPI) | Internal; also accessible for dev |

---

## 5. Firewall Configuration (If Needed)

```bash
# Allow frontend port through UFW
sudo ufw allow 3000/tcp

# Allow backend port (optional — for debugging only)
# sudo ufw allow 8000/tcp
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
