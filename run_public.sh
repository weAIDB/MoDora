#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.runtime/public"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"
URL_FILE="$RUNTIME_DIR/public_url.txt"
TUNNEL_LOG="$LOG_DIR/cloudflared.log"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
TUNNEL_BIN_LINK="$RUNTIME_DIR/cloudflared.current"

MODORA_API_PORT="${MODORA_API_PORT:-8005}"
MODORA_FRONTEND_PORT="${MODORA_FRONTEND_PORT:-5173}"
MODORA_FRONTEND_HOST="${MODORA_FRONTEND_HOST:-0.0.0.0}"
TUNNEL_PROTOCOL="${TUNNEL_PROTOCOL:-http2}"

mkdir -p "$LOG_DIR" "$PID_DIR"

backend_pid_file="$PID_DIR/backend.pid"
frontend_pid_file="$PID_DIR/frontend.pid"
tunnel_pid_file="$PID_DIR/tunnel.pid"

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

is_pid_running() {
    local pid="$1"
    kill -0 "$pid" >/dev/null 2>&1
}

pid_from_file() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

service_running() {
    local pid_file="$1"
    local pid
    pid="$(pid_from_file "$pid_file")"
    [ -n "${pid:-}" ] && is_pid_running "$pid"
}

start_detached() {
    local log_file="$1"
    shift

    nohup "$@" >"$log_file" 2>&1 </dev/null &
    echo $!
}

wait_for_http() {
    local url="$1"
    local attempts="${2:-60}"
    local i

    for ((i = 1; i <= attempts; i++)); do
        if curl --silent --fail --max-time 2 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    return 1
}

extract_tunnel_url() {
    if [ -f "$TUNNEL_LOG" ]; then
        grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -n 1
    fi
}

refresh_public_url() {
    local url
    url="$(extract_tunnel_url || true)"
    if [ -n "${url:-}" ]; then
        printf '%s\n' "$url" >"$URL_FILE"
    fi
}

wait_for_tunnel_url() {
    local attempts="${1:-60}"
    local i
    local url

    for ((i = 1; i <= attempts; i++)); do
        url="$(extract_tunnel_url || true)"
        if [ -n "${url:-}" ]; then
            printf '%s\n' "$url" >"$URL_FILE"
            echo "$url"
            return 0
        fi
        sleep 1
    done

    return 1
}

stop_service() {
    local pid_file="$1"
    local name="$2"
    local pid

    pid="$(pid_from_file "$pid_file")"
    if [ -z "${pid:-}" ]; then
        return 0
    fi

    if is_pid_running "$pid"; then
        kill "$pid" >/dev/null 2>&1 || true
        sleep 1
        if is_pid_running "$pid"; then
            kill -9 "$pid" >/dev/null 2>&1 || true
        fi
        echo "Stopped $name (PID $pid)"
    fi

    rm -f "$pid_file"
}

print_status() {
    local name="$1"
    local pid_file="$2"
    local pid

    pid="$(pid_from_file "$pid_file")"
    if [ -n "${pid:-}" ] && is_pid_running "$pid"; then
        echo "$name: running (PID $pid)"
    else
        echo "$name: stopped"
    fi
}

start_backend() {
    if service_running "$backend_pid_file"; then
        echo "Backend already running"
        return 0
    fi

    local pid
    pid="$(start_detached "$BACKEND_LOG" env MODORA_API_PORT="$MODORA_API_PORT" ./start_backend.sh)"
    printf '%s\n' "$pid" >"$backend_pid_file"
    echo "Started backend (PID $pid)"
}

start_frontend() {
    if service_running "$frontend_pid_file"; then
        echo "Frontend already running"
        return 0
    fi

    local pid
    pid="$(start_detached "$FRONTEND_LOG" env MODORA_API_PORT="$MODORA_API_PORT" MODORA_FRONTEND_HOST="$MODORA_FRONTEND_HOST" MODORA_FRONTEND_PORT="$MODORA_FRONTEND_PORT" ./start_frontend.sh)"
    printf '%s\n' "$pid" >"$frontend_pid_file"
    echo "Started frontend (PID $pid)"
}

start_tunnel() {
    if service_running "$tunnel_pid_file"; then
        echo "Tunnel already running"
        refresh_public_url
        if [ -f "$URL_FILE" ]; then
            echo "Public URL: $(cat "$URL_FILE")"
        fi
        return 0
    fi

    require_cmd cp
    require_cmd chmod

    local tunnel_bin="$PROJECT_ROOT/.tools/cloudflared"
    if [ ! -x "$tunnel_bin" ]; then
        echo "Missing Cloudflare Tunnel binary: $tunnel_bin" >&2
        exit 1
    fi

    local run_bin="$RUNTIME_DIR/cloudflared.$(date +%s).run"
    local launcher="$RUNTIME_DIR/cloudflared_launcher.sh"
    cp "$tunnel_bin" "$run_bin"
    chmod +x "$run_bin"
    ln -sfn "$run_bin" "$TUNNEL_BIN_LINK"
    cat >"$launcher" <<EOF
#!/bin/bash
set -euo pipefail

while true; do
    "$TUNNEL_BIN_LINK" tunnel --protocol "$TUNNEL_PROTOCOL" --url "http://127.0.0.1:$MODORA_FRONTEND_PORT" >>"$TUNNEL_LOG" 2>&1 || true
    sleep 2
done
EOF
    chmod +x "$launcher"
    : >"$TUNNEL_LOG"

    local pid
    pid="$(start_detached "$TUNNEL_LOG" "$launcher")"
    printf '%s\n' "$pid" >"$tunnel_pid_file"
    echo "Started tunnel (PID $pid, protocol $TUNNEL_PROTOCOL)"
}

start_all() {
    require_cmd nohup
    require_cmd curl

    cd "$PROJECT_ROOT"

    start_backend
    start_frontend

    if wait_for_http "http://127.0.0.1:$MODORA_FRONTEND_PORT" 90; then
        echo "Frontend is reachable on 127.0.0.1:$MODORA_FRONTEND_PORT"
    else
        echo "Frontend did not become reachable. Check $FRONTEND_LOG" >&2
        exit 1
    fi

    start_tunnel

    local url
    if url="$(wait_for_tunnel_url 60)"; then
        echo "Public URL: $url"
        echo "Saved to $URL_FILE"
    else
        echo "Tunnel started but URL was not detected. Check $TUNNEL_LOG" >&2
        exit 1
    fi

    echo "Logs:"
    echo "  Backend:  $BACKEND_LOG"
    echo "  Frontend: $FRONTEND_LOG"
    echo "  Tunnel:   $TUNNEL_LOG"
}

stop_all() {
    stop_service "$tunnel_pid_file" "tunnel"
    stop_service "$frontend_pid_file" "frontend"
    stop_service "$backend_pid_file" "backend"
    rm -f "$URL_FILE"
    rm -f "$TUNNEL_BIN_LINK"
}

status_all() {
    refresh_public_url
    print_status "Backend" "$backend_pid_file"
    print_status "Frontend" "$frontend_pid_file"
    print_status "Tunnel" "$tunnel_pid_file"
    if [ -f "$URL_FILE" ]; then
        echo "Public URL: $(cat "$URL_FILE")"
    fi
    echo "Tunnel protocol: $TUNNEL_PROTOCOL"
    echo "Logs:"
    echo "  Backend:  $BACKEND_LOG"
    echo "  Frontend: $FRONTEND_LOG"
    echo "  Tunnel:   $TUNNEL_LOG"
}

case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        status_all
        ;;
    restart)
        stop_all
        start_all
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}" >&2
        exit 1
        ;;
esac
