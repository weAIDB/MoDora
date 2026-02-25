#!/bin/bash

# MoDora Run Script

# This script now supports running in separate terminals using tmux 
# or simply pointing you to the separate start scripts.

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

# Find an available port for Backend (starting from 8005)
export MODORA_API_PORT=$(find_unused_port 8005)
echo "✅ Backend will use available port: $MODORA_API_PORT"

if command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    echo "🌐 Detected tmux! Starting backend and frontend in a split session..."
    tmux new-session -d -s modora "export MODORA_API_PORT=$MODORA_API_PORT; ./start_backend.sh"
    tmux split-window -h "export MODORA_API_PORT=$MODORA_API_PORT; ./start_frontend.sh"
    tmux attach-session -t modora
else
    echo "🚀 To run MoDora in separate terminals, please open two terminal tabs and run:"
    echo ""
    echo "  Terminal 1 (Backend): export MODORA_API_PORT=$MODORA_API_PORT && ./start_backend.sh"
    echo "  Terminal 2 (Frontend): export MODORA_API_PORT=$MODORA_API_PORT && ./start_frontend.sh"
    echo ""
    echo "Alternatively, you can run them both in this terminal (not recommended for log viewing):"
    echo "MODORA_API_PORT=$MODORA_API_PORT ./start_backend.sh & MODORA_API_PORT=$MODORA_API_PORT ./start_frontend.sh"
fi
