#!/bin/bash
set -e

# Multi-Architecture Playwright Testing Script
# Tests ARM64, AMD64, and CUDA builds systematically

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🎯 Multi-Architecture Playwright Testing"
echo "========================================"

# Initialize test results (compatible with older bash)
ARM64_RESULT="NOT_RUN"
AMD64_RESULT="NOT_RUN"
CUDA_RESULT="NOT_RUN"

# Function to test architecture
test_architecture() {
    local arch="$1"
    local platform="$2"
    local compose_extra="$3"
    
    echo "🔧 Testing $arch architecture..."
    
    # Set platform environment
    export DOCKER_DEFAULT_PLATFORM="$platform"
    
    # Build the image
    echo "📦 Building $arch container..."
    if [ -n "$compose_extra" ]; then
        # CUDA build
        docker compose -f docker/docker-compose.yaml -f docker/docker-compose.gpu.yaml build
    else
        docker compose -f docker/docker-compose.yaml build
    fi
    
    # Start container
    echo "🚀 Starting $arch container..."
    if [ -n "$compose_extra" ]; then
        docker compose -f docker/docker-compose.yaml -f docker/docker-compose.gpu.yaml up -d
    else
        docker compose -f docker/docker-compose.yaml up -d
    fi
    
    # Wait for container to be ready
    echo "⏳ Waiting for server to be ready..."
    for i in {1..30}; do
        if docker exec mcts curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "✅ Server is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Server failed to start"
            return 1
        fi
        sleep 1
    done
    
    # Check architecture
    echo "🔍 Verifying architecture..."
    arch_result=$(docker exec mcts arch)
    echo "Container architecture: $arch_result"
    
    # Check Playwright browsers
    echo "🎭 Checking Playwright browsers..."
    if docker exec mcts ls -la /home/mcts/.cache/ms-playwright/ | grep -q chromium; then
        echo "✅ Browsers are installed"
    else
        echo "❌ Browsers not found"
        return 1
    fi
    
    # Run E2E tests
    echo "🧪 Running E2E tests..."
    if docker exec mcts bash -c 'export E2E_FRONTEND_URL="http://127.0.0.1:8000" E2E_BACKEND_URL="http://127.0.0.1:8000" E2E_WS_URL="ws://127.0.0.1:8000/ws" && timeout 180 poetry run pytest tests/e2e/test_browser_compatibility.py::TestBrowserCompatibility::test_all_browsers_load_frontend -v'; then
        echo "✅ $arch E2E tests PASSED"
        case "$arch" in
            "ARM64") ARM64_RESULT="PASS" ;;
            "AMD64") AMD64_RESULT="PASS" ;;
            "CUDA") CUDA_RESULT="PASS" ;;
        esac
    else
        echo "❌ $arch E2E tests FAILED"
        case "$arch" in
            "ARM64") ARM64_RESULT="FAIL" ;;
            "AMD64") AMD64_RESULT="FAIL" ;;
            "CUDA") CUDA_RESULT="FAIL" ;;
        esac
    fi
    
    # Cleanup
    echo "🧹 Cleaning up $arch container..."
    if [ -n "$compose_extra" ]; then
        docker compose -f docker/docker-compose.yaml -f docker/docker-compose.gpu.yaml down
    else
        docker compose -f docker/docker-compose.yaml down
    fi
    
    echo ""
}

cd "$PROJECT_ROOT"

# Test ARM64 (native on Apple Silicon)
test_architecture "ARM64" "linux/arm64" ""

# Test AMD64 (emulated on Apple Silicon)
test_architecture "AMD64" "linux/amd64" ""

# Test CUDA (AMD64 + CUDA, emulated on Apple Silicon)
test_architecture "CUDA" "linux/amd64" "gpu"

# Summary
echo "📊 TEST RESULTS SUMMARY"
echo "======================="
all_passed=true
echo "ARM64: $ARM64_RESULT"
echo "AMD64: $AMD64_RESULT"
echo "CUDA: $CUDA_RESULT"

if [ "$ARM64_RESULT" != "PASS" ] || [ "$AMD64_RESULT" != "PASS" ] || [ "$CUDA_RESULT" != "PASS" ]; then
    all_passed=false
fi

if [ "$all_passed" = true ]; then
    echo "🎉 ALL ARCHITECTURES PASSED!"
    exit 0
else
    echo "💥 SOME ARCHITECTURES FAILED!"
    exit 1
fi