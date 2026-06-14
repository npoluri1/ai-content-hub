FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# For Playwright (optional)
RUN pip install playwright && playwright install chromium 2>/dev/null || true

# Expose API and health check
EXPOSE 8000 8501

# Default: run API server
CMD ["python", "-m", "pipeline", "api"]
