#!/bin/bash
# Deploy agent worker + case API to the EC2 box, restart both, verify.
set -euo pipefail
cd "$(dirname "$0")/.."

# Host and key live in scripts/deploy.env, which is untracked. Copy
# scripts/deploy.env.example and fill it in. Nothing identifying the box
# belongs in a file that gets committed.
if [ -f scripts/deploy.env ]; then
  # shellcheck disable=SC1091
  source scripts/deploy.env
fi

: "${DISHA_DEPLOY_HOST:?set DISHA_DEPLOY_HOST in scripts/deploy.env}"
: "${DISHA_DEPLOY_KEY:?set DISHA_DEPLOY_KEY in scripts/deploy.env}"

EC2="$DISHA_DEPLOY_HOST"
PEM="$DISHA_DEPLOY_KEY"

rsync -az -e "ssh -i $PEM" \
  --exclude .venv --exclude __pycache__ --exclude cases --exclude raw \
  agent api data .env Makefile ${EC2}:~/disha/

ssh -i "$PEM" "$EC2" 'bash -s' <<'REMOTE'
set -e
cd ~/disha
if [ ! -d .venv ]; then python3 -m venv .venv; fi
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q livekit-agents livekit-plugins-sarvam livekit-plugins-silero \
  python-dotenv aiohttp fastapi uvicorn
pkill -f "main.py start" 2>/dev/null || true
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1
mkdir -p agent/cases
(cd agent && nohup ../.venv/bin/python main.py start > ../agent.log 2>&1 &)
(cd api && DISHA_CASES_DIR=$HOME/disha/agent/cases nohup ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8090 > ../api.log 2>&1 &)
sleep 5
echo "--- agent.log ---"; tail -5 ~/disha/agent.log
echo "--- api health ---"; curl -s localhost:8090/health; echo
REMOTE
echo "deploy-ec2 done"
