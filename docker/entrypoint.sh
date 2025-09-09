#!/bin/bash
set -e

echo "🚀 Starting MCTS container setup..."

# Install Playwright browsers if not already installed
if [ ! -d "/home/mcts/.cache/ms-playwright" ] || [ -z "$(ls -A /home/mcts/.cache/ms-playwright 2>/dev/null)" ]; then
    echo "📥 Installing Playwright browsers for $(arch) architecture..."
    playwright install
    echo "✅ Playwright browsers installed"
else
    echo "✅ Playwright browsers already installed"
fi

# Check and build frontend if needed
if [ ! -d "/app/frontend/build" ] || [ -z "$(ls -A /app/frontend/build 2>/dev/null)" ]; then
    echo "📦 Building frontend (not found or empty)..."
    cd /app/frontend
    
    # Remove potentially corrupted package-lock.json on ARM64
    if [ "$(dpkg --print-architecture)" = "arm64" ]; then
        echo "🔧 ARM64 detected: Using fresh npm install"
        rm -f package-lock.json
    fi
    
    # Try npm install
    if npm install; then
        echo "✅ npm install succeeded"
        # Build the frontend
        if npm run build; then
            echo "✅ Frontend build complete"
        else
            echo "❌ Frontend build failed - backend will still work"
        fi
    else
        echo "❌ npm install failed - backend will still work"
    fi
else
    echo "✅ Frontend build already exists"
fi

# Check and build C++ backend if needed
if [ ! -f "/app/backend/python/corridors/_corridors_mcts.so" ]; then
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