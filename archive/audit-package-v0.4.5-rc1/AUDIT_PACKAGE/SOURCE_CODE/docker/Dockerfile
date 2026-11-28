FROM python:3.11-slim

LABEL maintainer="Luis Alberto Burciaga Miker <luis@solvens.amoris>"
LABEL description="SOLVENS CORE - AI Operating System"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml* ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[all]"

# Copy application code
COPY solvens/ ./solvens/
COPY docs/ ./docs/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SOLVENS_DATA_DIR=/data

# Create data directory
RUN mkdir -p /data

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run API server
CMD ["uvicorn", "solvens.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
