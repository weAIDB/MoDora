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
    # Note: If start_backend.sh is run separately without env var, it will also use this logic
    export MODORA_API_PORT=$(find_unused_port 8005)
    echo "⚠️ MODORA_API_PORT not set, auto-detected available port: $MODORA_API_PORT"
fi

# Run Vite
npm run dev
