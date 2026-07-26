# One image, three roles. The agent worker, the case API, and the one-shot
# indexer all import the same modules and read the same data/ files, so building
# them separately would only create a way for them to drift apart. The role is
# chosen by the command in docker-compose.yml.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libgomp is required by the Silero VAD ONNX runtime; curl is the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY api/ ./api/
COPY data/ ./data/
COPY scripts/index_kb.py ./scripts/index_kb.py

# Fetch the Silero VAD weights at build time. Without this the first call of a
# fresh container pays the download, which shows up as dead air on the line.
RUN cd agent && python main.py download-files || \
    echo "model prefetch skipped; the worker will download on first start"

# Cases are written by the agent and read by the API, so both mount this path.
RUN mkdir -p /app/agent/cases
ENV DISHA_CASES_DIR=/app/agent/cases \
    QDRANT_URL=http://sarvam-qdrant:6333

# Non-root: nothing here needs to write outside /app.
RUN useradd --create-home --uid 10001 disha \
    && chown -R disha:disha /app
USER disha

CMD ["python", "agent/main.py", "start"]
