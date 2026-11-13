# Backend: FastAPI + LangGraph + static analyzers.
FROM python:3.12-slim

# git is needed to clone GitHub repositories for auditing.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# semgrep scans JS/TS. It goes in its own virtualenv because its
# dependencies conflict with FastAPI's and ChromaDB's pinned versions.
ARG INSTALL_SEMGREP=true
RUN if [ "$INSTALL_SEMGREP" = "true" ]; then \
        python -m venv /opt/semgrep \
        && /opt/semgrep/bin/pip install --no-cache-dir semgrep==1.185.0 \
        && ln -s /opt/semgrep/bin/semgrep /usr/local/bin/semgrep; \
    fi

COPY src ./src
COPY backend ./backend
COPY rules ./rules

# Run as an unprivileged user; /data holds the audit history.
RUN useradd --create-home --uid 10001 auditor \
    && mkdir -p /data && chown auditor:auditor /data
USER auditor

ENV DATA_DIR=/data \
    OLLAMA_BASE_URL=http://ollama:11434 \
    PYTHONUNBUFFERED=1 \
    SEMGREP_SEND_METRICS=off

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# 0.0.0.0 inside the container only; docker-compose.yml publishes the port
# on the host's 127.0.0.1, so it is not reachable from your network.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
