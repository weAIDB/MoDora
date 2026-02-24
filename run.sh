#!/bin/bash

# MoDora Run Script

# This script now supports running in separate terminals using tmux 
# or simply pointing you to the separate start scripts.

# Function to find an unused port
find_unused_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; do
        port=$((port + 1))
    done
    echo $port
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
