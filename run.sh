#!/bin/bash

# MoDora Run Script

# This script now supports running in separate terminals using tmux 
# or simply pointing you to the separate start scripts.

if command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    echo "🌐 Detected tmux! Starting backend and frontend in a split session..."
    tmux new-session -d -s modora './start_backend.sh'
    tmux split-window -h './start_frontend.sh'
    tmux attach-session -t modora
else
    echo "🚀 To run MoDora in separate terminals, please open two terminal tabs and run:"
    echo ""
    echo "  Terminal 1 (Backend): ./start_backend.sh"
    echo "  Terminal 2 (Frontend): ./start_frontend.sh"
    echo ""
    echo "Alternatively, you can run them both in this terminal (not recommended for log viewing):"
    echo "./start_backend.sh & ./start_frontend.sh"
fi
