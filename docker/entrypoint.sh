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

# Check and build C++ backend if needed with architecture awareness
ARCH=$(dpkg --print-architecture)
SO_PATH="/app/backend/python/corridors/_corridors_mcts.so"
ARCH_SO_PATH="/app/backend/python/corridors/_corridors_mcts_${ARCH}.so"

echo "🔍 Checking C++ backend for architecture: $ARCH"

# Remove any existing .so file that doesn't match current architecture
if [ -f "$SO_PATH" ]; then
    # Use file command to detect architecture, with fallback to always rebuild if detection fails
    if command -v file >/dev/null 2>&1; then
        EXISTING_ARCH=$(file -L "$SO_PATH" | grep -o "x86-64\|ARM aarch64" | head -1)
        echo "🔍 Detected existing .so architecture: $EXISTING_ARCH"
        if [ "$ARCH" = "amd64" ] && [ "$EXISTING_ARCH" != "x86-64" ]; then
            echo "🗑️  Removing incompatible .so file (found $EXISTING_ARCH, need x86-64)"
            rm -f "$SO_PATH"
        elif [ "$ARCH" = "arm64" ] && [ "$EXISTING_ARCH" != "ARM aarch64" ]; then
            echo "🗑️  Removing incompatible .so file (found $EXISTING_ARCH, need ARM aarch64)"
            rm -f "$SO_PATH"
        fi
    else
        echo "⚠️  'file' command not available, removing existing .so to force rebuild"
        rm -f "$SO_PATH"
    fi
fi

# Check if we have the right architecture-specific .so file
if [ -f "$ARCH_SO_PATH" ] && [ ! -f "$SO_PATH" ]; then
    echo "🔗 Linking architecture-specific .so file for $ARCH"
    
    # Validate that the architecture-specific file is actually the right architecture
    if command -v file >/dev/null 2>&1; then
        ARCH_SO_DETECTED=$(file -L "$ARCH_SO_PATH" | grep -o "x86-64\|ARM aarch64" | head -1)
        EXPECTED_ARCH=""
        if [ "$ARCH" = "amd64" ]; then
            EXPECTED_ARCH="x86-64"
        elif [ "$ARCH" = "arm64" ]; then
            EXPECTED_ARCH="ARM aarch64"
        fi
        
        if [ "$ARCH_SO_DETECTED" != "$EXPECTED_ARCH" ]; then
            echo "⚠️  Architecture-specific .so file has wrong architecture (found $ARCH_SO_DETECTED, expected $EXPECTED_ARCH)"
            echo "🗑️  Removing contaminated architecture-specific .so file"
            rm -f "$ARCH_SO_PATH"
        else
            echo "✅ Architecture-specific .so file validated for $ARCH"
            cd /app/backend/python/corridors
            ln -sf "_corridors_mcts_${ARCH}.so" "_corridors_mcts.so"
            echo "✅ C++ backend linked for $ARCH"
        fi
    else
        echo "⚠️  Cannot validate architecture-specific file, creating symlink anyway"
        cd /app/backend/python/corridors
        ln -sf "_corridors_mcts_${ARCH}.so" "_corridors_mcts.so"
        echo "✅ C++ backend linked for $ARCH"
    fi
elif [ ! -f "$SO_PATH" ]; then
    echo "🔧 Building C++ backend for $ARCH (not found)..."
    cd /app/backend/core
    scons -c -Q  # Clean first for fresh build
    scons -Q
    if [ -f "$SO_PATH" ]; then
        # Create architecture-specific copy and symlink
        cp "$SO_PATH" "$ARCH_SO_PATH"
        echo "✅ C++ backend build complete for $ARCH"
    else
        echo "❌ C++ backend build failed"
        exit 1
    fi
else
    echo "✅ C++ backend already built for $ARCH"
fi

echo "🎯 Starting server on port 8000..."
cd /app
exec poetry run server