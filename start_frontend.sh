#!/bin/bash

# MoDora Frontend Starter

set -e

echo "💻 Starting Frontend Dev Server..."
cd MoDora-frontend

# Check for node_modules
if [ ! -d "node_modules" ]; then
    echo "❌ node_modules not found. Please run ./setup.sh first."
    exit 1
fi

# Function to find an unused port
find_unused_port() {
    local port=$1
    while true; do
        # Try to bind using python as it is the most reliable cross-user check
        if command -v python3 >/dev/null 2>&1; then
            if python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.bind(('0.0.0.0', $port)); s.close()" >/dev/null 2>&1; then
                echo $port
                return
            fi
        # Fallback to lsof if python is not available
        elif command -v lsof >/dev/null 2>&1; then
            if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
                echo $port
                return
            fi
        else
            # If no tools available, just return the port and hope for the best
            echo $port
            return
        fi
        port=$((port + 1))
    done
}

# Determine backend port for proxy
if [ -z "$MODORA_API_PORT" ]; then
    # Try to find what port the backend might be using (default logic)
    # 1. Try to read from root local.json
    if [ -f "../local.json" ] && command -v python3 &>/dev/null; then
        CONFIG_PORT=$(python3 -c "import json; print(json.load(open('../local.json')).get('api_port', ''))" 2>/dev/null)
        if [ -n "$CONFIG_PORT" ]; then
            export MODORA_API_PORT=$CONFIG_PORT
            echo "📝 Found MODORA_API_PORT in local.json: $MODORA_API_PORT"
        fi
    fi
fi

if [ -z "$MODORA_API_PORT" ]; then
    # 2. Default to 8005 (don't use find_unused_port as it finds a port NOT in use)
    export MODORA_API_PORT=8005
    echo "💡 Using default MODORA_API_PORT: $MODORA_API_PORT"
fi

echo "🚀 Frontend will proxy to API on port: $MODORA_API_PORT"

# Run Vite
npm run dev
