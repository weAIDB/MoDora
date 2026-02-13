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

# Run Vite
npm run dev
