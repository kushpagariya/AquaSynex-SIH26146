# Docker Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Services

| Service | Container Name | Image | Port |
|---|---|---|---|
| Frontend | `aquasynex-frontend` | Built from `./frontend/Dockerfile` | `3000:80` |
| Backend | `aquasynex-backend` | Built from `./backend/Dockerfile` | `8000:8000` |

No separate ML service — ML pipeline runs in-process within the backend container.

---

## 2. Volumes

| Volume | Mount (Backend) | Purpose |
|---|---|---|
| `aquasynex-data` | `/app/data` | Dataset files uploaded by investigator |
| `aquasynex-db` | `/app/db` | DuckDB database files |
| `aquasynex-models` | `/app/models` | Trained ML model artifacts |

---

## 3. Docker Compose Configuration (Proposed)

```yaml
# docker-compose.yml (PLANNED)
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: aquasynex-backend
    ports:
      - "8000:8000"
    environment:
      - DB_PATH=/app/db/aquasynex.db
      - DATA_DIR=/app/data
      - MODELS_DIR=/app/models
      - LOG_LEVEL=INFO
    volumes:
      - aquasynex-data:/app/data
      - aquasynex-db:/app/db
      - aquasynex-models:/app/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - aquasynex-net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: /api    # Relative — Nginx proxies /api to backend
    container_name: aquasynex-frontend
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - aquasynex-net

volumes:
  aquasynex-data:
  aquasynex-db:
  aquasynex-models:

networks:
  aquasynex-net:
    driver: bridge
```

---

## 4. Backend Dockerfile (Proposed)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (requires internet during build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/db /app/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 5. Frontend Dockerfile (Proposed)

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (requires internet during build)
COPY package*.json ./
RUN npm ci

# Build with API URL
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

---

## 6. Nginx Configuration (Proposed)

```nginx
# nginx.conf
server {
    listen 80;
    server_name _;
    
    # Serve frontend build
    root /usr/share/nginx/html;
    index index.html;
    
    # SPA routing — all routes return index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Increase timeout for file uploads and long analyses
        proxy_read_timeout 300s;
        client_max_body_size 2048m;
    }
}
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner + Frontend Owner*
*References: [deployment-architecture.md](../architecture/deployment-architecture.md) | [offline-deployment.md](./offline-deployment.md)*
