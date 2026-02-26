#!/bin/bash

# MoDora Backend Starter

set -e

echo "🔧 Starting Backend API..."
cd MoDora-backend

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

source venv/bin/activate

# Auto-load config if exists
if [ -f "../local.json" ]; then
    echo "📝 Loading configuration from local.json"
    export MODORA_CONFIG="../local.json"
elif [ -f "configs/local.json" ]; then
    echo "📝 Loading configuration from configs/local.json"
    export MODORA_CONFIG="configs/local.json"
fi

# Check if MODORA_API_KEY is set
if [ -z "$MODORA_API_KEY" ]; then
    echo "⚠️  Warning: MODORA_API_KEY is not set."
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

# Determine port from config, env, or auto-detect
if [ -n "$MODORA_API_PORT" ]; then
    API_PORT=$MODORA_API_PORT
elif [ -f "$MODORA_CONFIG" ] && command -v python3 &>/dev/null; then
    CONFIG_PORT=$(python3 -c "import json; print(json.load(open('$MODORA_CONFIG')).get('api_port', ''))" 2>/dev/null)
    if [ -n "$CONFIG_PORT" ]; then
        API_PORT=$CONFIG_PORT
    else
        API_PORT=$(find_unused_port 8005)
    fi
else
    API_PORT=$(find_unused_port 8005)
fi

export MODORA_API_PORT=$API_PORT
echo "🚀 API will listen on port: $API_PORT"

# Run FastAPI
uvicorn modora.api.app:app --host 0.0.0.0 --port "$API_PORT" --reload
