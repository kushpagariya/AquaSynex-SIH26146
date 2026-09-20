# AquaSynex Backend Dockerfile
# Python 3.11 Linux base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install minimal OS dependencies:
# - curl: for container healthchecks
# - libgomp1: required by XGBoost and CatBoost for OpenMP multithreading on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir \
    --default-timeout=1000 \
    --retries=10 \
    -r /app/backend/requirements.txt
# Copy required source directories and model artifacts
COPY backend /app/backend
COPY ml /app/ml
COPY pipeline /app/pipeline
COPY models /app/models
COPY datasets /app/datasets

# Ensure runtime directories exist and have appropriate permissions
RUN mkdir -p /app/data

# Expose backend port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
