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
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; do
        port=$((port + 1))
    done
    echo $port
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
