# SOLVENS CORE - Dockerfile
# Multi-stage build for production

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml ./
COPY cosmos/ ./cosmos/
COPY solvens/ ./solvens/

# Install dependencies
RUN pip install --no-cache-dir --user -e .

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY --from=builder /app/cosmos/ ./cosmos/
COPY --from=builder /app/solvens/ ./solvens/

# Create non-root user
RUN useradd -m -u 1000 solvens
USER solvens

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import cosmos; print('ok')" || exit 1

# Default command
CMD ["solvens", "doctor"]
