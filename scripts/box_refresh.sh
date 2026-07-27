#!/bin/bash
# Nightly data refresh, box side.
#
# The deployment box cannot pull the ghcr images, so it runs a locally built
# image. Data lives INSIDE that image (Dockerfile: `COPY data/ ./data/`), not on
# a bind mount, so a fresh data/dynamic on disk only reaches the containers after
# the image is rebuilt. The path is therefore:
#   1. git pull             -> new data/dynamic/*.json land on disk
#   2. docker compose build -> bake the refreshed data into the local image
#   3. run the indexer      -> re-embed every collection into Qdrant
#   4. restart the agent    -> it reloads data/*.json at import
#
# Nothing here pulls from ghcr. If the box instead bind-mounts ./data into the
# indexer and agent services, delete the `docker compose build` line: the pull
# alone then makes the new data visible.
#
# Point DISHA_REPO at the checkout if it is not the parent of this script.
set -euo pipefail

REPO="${DISHA_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO"

echo "[box-refresh] $(date -u +%FT%TZ) pulling latest data"
git pull --ff-only

echo "[box-refresh] rebuilding image with refreshed data"
docker compose build sarvam-indexer sarvam-agent

echo "[box-refresh] re-embedding knowledge base"
docker compose run --rm sarvam-indexer

echo "[box-refresh] restarting agent"
docker compose up -d --force-recreate sarvam-agent

echo "[box-refresh] done"
