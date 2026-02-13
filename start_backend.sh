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
if [ -f "configs/local.json" ]; then
    echo "📝 Loading configuration from configs/local.json"
    export MODORA_CONFIG="configs/local.json"
fi

# Check if MODORA_API_KEY is set
if [ -z "$MODORA_API_KEY" ]; then
    echo "⚠️  Warning: MODORA_API_KEY is not set."
fi

# Run FastAPI
uvicorn modora.api.app:app --host 0.0.0.0 --port 8000 --reload
