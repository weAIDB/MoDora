#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELAY_HOST="${RELAY_HOST:-42.193.125.159}"
RELAY_USER="${RELAY_USER:-ubuntu}"
API_PORT="${MODORA_API_PORT:-8005}"
FRONTEND_PORT="${MODORA_FRONTEND_PORT:-5173}"
FRONTEND_HOST="${MODORA_FRONTEND_HOST:-0.0.0.0}"
RELAY_FRONTEND_PORT="${RELAY_FRONTEND_PORT:-18080}"
RELAY_API_PORT="${RELAY_API_PORT:-18081}"
WAIT_SECONDS="${WAIT_SECONDS:-5}"

BACKEND_LOG="${BACKEND_LOG:-/tmp/modora-backend.log}"
FRONTEND_LOG="${FRONTEND_LOG:-/tmp/modora-frontend.log}"
RELAY_FRONTEND_LOG="${RELAY_FRONTEND_LOG:-/tmp/modora-relay-frontend.log}"
RELAY_API_LOG="${RELAY_API_LOG:-/tmp/modora-relay-api.log}"

stop_matching() {
    local pattern="$1"
    pkill -f "$pattern" >/dev/null 2>&1 || true
}

status_hint() {
    echo "Logs:"
    echo "  backend:  $BACKEND_LOG"
    echo "  frontend: $FRONTEND_LOG"
    echo "  relay frontend: $RELAY_FRONTEND_LOG"
    echo "  relay api:      $RELAY_API_LOG"
    echo "Public URL: http://$RELAY_HOST"
}

start_all() {
    cd "$PROJECT_ROOT"

    stop_matching "uvicorn"
    stop_matching "node .*vite"
    stop_matching "ssh .*0.0.0.0:$RELAY_FRONTEND_PORT:127.0.0.1:$FRONTEND_PORT"
    stop_matching "ssh .*0.0.0.0:$RELAY_API_PORT:127.0.0.1:$API_PORT"

    sleep "$WAIT_SECONDS"

    nohup env MODORA_API_PORT="$API_PORT" ./start_backend.sh >"$BACKEND_LOG" 2>&1 &
    nohup env MODORA_API_PORT="$API_PORT" MODORA_FRONTEND_HOST="$FRONTEND_HOST" MODORA_FRONTEND_PORT="$FRONTEND_PORT" VITE_MODORA_PUBLIC_API_PORT="$RELAY_API_PORT" ./start_frontend.sh >"$FRONTEND_LOG" 2>&1 &

    sleep "$WAIT_SECONDS"

    nohup ssh \
        -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -N \
        -R 0.0.0.0:"$RELAY_FRONTEND_PORT":127.0.0.1:"$FRONTEND_PORT" \
        "$RELAY_USER@$RELAY_HOST" >"$RELAY_FRONTEND_LOG" 2>&1 &

    nohup ssh \
        -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -N \
        -R 0.0.0.0:"$RELAY_API_PORT":127.0.0.1:"$API_PORT" \
        "$RELAY_USER@$RELAY_HOST" >"$RELAY_API_LOG" 2>&1 &

    echo "Started MoDora backend, frontend, and Tencent relays."
    status_hint
}

stop_all() {
    stop_matching "uvicorn"
    stop_matching "node .*vite"
    stop_matching "ssh .*0.0.0.0:$RELAY_FRONTEND_PORT:127.0.0.1:$FRONTEND_PORT"
    stop_matching "ssh .*0.0.0.0:$RELAY_API_PORT:127.0.0.1:$API_PORT"
    echo "Stopped backend, frontend, and relays."
}

case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep "$WAIT_SECONDS"
        start_all
        ;;
    status)
        ps -ef | grep -E "uvicorn|vite|0.0.0.0:$RELAY_FRONTEND_PORT:127.0.0.1:$FRONTEND_PORT|0.0.0.0:$RELAY_API_PORT:127.0.0.1:$API_PORT" | grep -v grep || true
        status_hint
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}" >&2
        exit 1
        ;;
esac
