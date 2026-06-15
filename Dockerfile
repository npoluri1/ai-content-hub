# =============================================================================
# AI Content Hub — Multi-Stage Dockerfile
# Supports: CI/CD builds, local dev, Docker Compose, external tools
# =============================================================================
# Build targets:
#   backend   — FastAPI server (default)
#   frontend  — Nginx serving built frontend assets
#   fullstack — Backend + Nginx frontend in one image
# =============================================================================

# ============================================================
# STAGE 0: Python base — shared deps layer
# ============================================================
FROM python:3.12-slim AS python-base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# STAGE 1: Backend (default target)
# ============================================================
FROM python-base AS backend

WORKDIR /app

COPY --from=python-base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

COPY . .

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "pipeline", "api"]

# ============================================================
# STAGE 2: Frontend builder
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ============================================================
# STAGE 3: Frontend (nginx)
# ============================================================
FROM nginx:alpine AS frontend

COPY --from=frontend-builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

# ============================================================
# STAGE 4: Full stack (backend + frontend proxy)
# Default target for docker compose / local deployment
# ============================================================
FROM python-base AS fullstack

WORKDIR /app

# Python runtime
COPY --from=python-base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin
COPY . .

# Frontend build
COPY --from=frontend-builder /app/dist /app/frontend/dist

EXPOSE 8000 80

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "pipeline", "api"]
