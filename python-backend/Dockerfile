# Stage 1: builder — install dependencies and build wheel
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy dependency specification and source code
COPY pyproject.toml .
COPY src/ src/

# Build the wheel
RUN python -m build --wheel

# Stage 2: runtime — minimal image with only runtime dependencies
FROM python:3.12-slim AS runtime

# Install runtime system dependencies (libpq for psycopg)
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install the built wheel
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create logs directory for daily rotation
RUN mkdir -p logs

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
