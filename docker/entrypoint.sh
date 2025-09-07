#!/bin/bash
set -e

echo "🚀 Starting MCTS container setup..."

# Check and build frontend if needed
if [ ! -d "/app/frontend/build" ] || [ -z "$(ls -A /app/frontend/build 2>/dev/null)" ]; then
    echo "📦 Building frontend (not found or empty)..."
    cd /app/frontend
    npm ci
    npm run build
    echo "✅ Frontend build complete"
else
    echo "✅ Frontend build already exists"
fi

# Check and build C++ backend if needed
if [ ! -f "/app/backend/core/_corridors_mcts.so" ]; then
    echo "🔧 Building C++ backend (not found)..."
    cd /app/backend/core
    scons -c -Q  # Clean first for fresh build
    scons -Q
    echo "✅ C++ backend build complete"
else
    echo "✅ C++ backend already built"
fi

echo "🎯 Starting server on port 8000..."
cd /app
exec poetry run server