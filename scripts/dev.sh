#!/bin/bash
# Start agent worker + case API in the background, web dev server in the
# foreground. Ctrl-C tears everything down.
set -uo pipefail
cd "$(dirname "$0")/.."

# Seconds to let a child shut down gracefully before it is killed outright.
# The LiveKit worker installs its own SIGINT handler and drains active jobs,
# which can outlast a demo reset if a room session is still open.
GRACE_S="${DEV_SHUTDOWN_GRACE_S:-5}"

pids=()

shutdown() {
    trap - EXIT INT TERM  # never re-enter this handler

    for pid in "${pids[@]}"; do
        kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
    done

    # Escalate rather than wait forever: a draining worker with an open room
    # session will not exit on its own within any useful demo turnaround.
    for _ in $(seq "$((GRACE_S * 4))"); do
        local_alive=0
        for pid in "${pids[@]}"; do
            kill -0 "$pid" 2>/dev/null && local_alive=1
        done
        [ "$local_alive" -eq 0 ] && break
        sleep 0.25
    done

    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "[dev] force-killing $pid" >&2
            kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
        fi
    done

    # Backstop: anything started by a previous run that outlived its parent.
    pkill -f "main.py dev" 2>/dev/null
    pkill -f "uvicorn main:app" 2>/dev/null
}

trap shutdown EXIT INT TERM

# Process substitution, not a pipe: for `cmd | sed &` the shell reports sed's
# PID in $!, so the worker itself would survive every kill we sent.
bash -c 'cd agent && exec .venv/bin/python main.py dev' \
    > >(sed 's/^/[agent] /') 2>&1 &
pids+=($!)

bash -c 'cd api && exec ../agent/.venv/bin/python -m uvicorn main:app --port 8090' \
    > >(sed 's/^/[api] /') 2>&1 &
pids+=($!)

sleep 1
cd web && npm run dev
