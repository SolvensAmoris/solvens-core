# Build-time network access is used only to install declared dependencies.
# Anthropic's audit phase runs the resulting image without network access.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src

# Keep the complete repository available to the offline auditor.
COPY . /src

# Install runtime extras used by the API and storage layers, plus test tools.
# The optional vector/ML extra pulls a large model stack; its source remains
# available for static review but that optional runtime is not installed here.
RUN python -m pip install --no-cache-dir ".[api,storage,dev]" \
    && python -m compileall -q cosmos solvens security

# Fail the image build if the maintained Python test suite fails.
RUN python -m pytest tests/ -q

# The scanner can rerun tests inside its network-isolated audit container.
CMD ["python", "-m", "pytest", "tests/", "-q"]
