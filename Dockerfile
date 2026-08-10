# ── Build Stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for chromadb (sqlite3) and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY core/ core/
COPY server/ server/
COPY ui/ ui/
COPY utils/ utils/
COPY skills/ skills/
COPY app/ app/
COPY knowledge/ knowledge/
COPY run_server.py miminox.py ./

RUN pip install --no-cache-dir .

# ── Runtime Stage ────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 curl openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages + app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build /app

# Persistent data: memory, sessions, skills, profile
VOLUME ["/root/.mimi-nox"]

EXPOSE 8765

# Health check against /api/health
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8765/api/health || exit 1

# Default: Start web server
CMD ["python", "run_server.py", "--host", "0.0.0.0", "--port", "8765"]
