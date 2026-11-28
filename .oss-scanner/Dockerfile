# SOLVENS CORE: reproducible environment for Anthropic OSS Scanner.
# Build has network access; the scanner's audit phase runs offline.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/solvens-core

# pyproject.toml declares README.md as package metadata.
COPY pyproject.toml README.md ./
COPY cosmos/ ./cosmos/
COPY solvens/ ./solvens/
COPY tests/ ./tests/

# Install the project and its test/development dependencies during image build.
RUN python -m pip install --no-cache-dir ".[dev]" \
    && python -m compileall -q cosmos solvens

# Run the complete repository test suite at build time. A failed test fails the image.
RUN python -m pytest tests/ -q

# Keep the source tree and test runner available to the offline security auditor.
CMD ["python", "-m", "pytest", "tests/", "-q"]
