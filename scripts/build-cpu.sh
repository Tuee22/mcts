#!/bin/bash
#
# CPU-Only Docker Build Helper Script
# Builds optimized containers for CPU-only environments
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="${MCTS_CPU_IMAGE:-mcts-cpu}"
BUILD_CONTEXT="${PROJECT_ROOT}"
DOCKERFILE="${PROJECT_ROOT}/docker/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
CPU-Only Docker Build Helper

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -t, --tag TAG       Set image tag (default: mcts-cpu)
    -f, --dockerfile    Dockerfile path (default: docker/Dockerfile.cpu)
    --no-cache          Build without using cache
    --buildkit          Use Docker BuildKit
    --push              Push image after successful build
    --dry-run           Show commands without executing
    --verbose           Enable verbose output

ENVIRONMENT VARIABLES:
    MCTS_CPU_IMAGE      Image name (default: mcts-cpu)
    DOCKER_BUILDKIT     Enable BuildKit (0 or 1)
    BUILD_THREADS       Number of build threads
    TARGET_ARCH         Target architecture (x86_64, arm64)

EXAMPLES:
    # Basic build
    $0

    # Build with custom tag
    $0 --tag mcts-cpu:v1.2.3

    # Build without cache
    $0 --no-cache

    # Build with BuildKit enabled
    $0 --buildkit

    # Cross-platform build
    TARGET_ARCH=arm64 $0 --tag mcts-cpu:arm64

EOF
}

# Parse command line arguments
DOCKER_TAG="${IMAGE_NAME}:latest"
DOCKERFILE_PATH="${DOCKERFILE}"
USE_CACHE="--cache-from ${IMAGE_NAME}:latest"
USE_BUILDKIT="${DOCKER_BUILDKIT:-0}"
PUSH_IMAGE=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--tag)
            DOCKER_TAG="$2"
            shift 2
            ;;
        -f|--dockerfile)
            DOCKERFILE_PATH="$2"
            shift 2
            ;;
        --no-cache)
            USE_CACHE="--no-cache"
            shift
            ;;
        --buildkit)
            USE_BUILDKIT=1
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Verbose mode
if [[ "$VERBOSE" == "true" ]]; then
    set -x
fi

# Pre-build checks
check_requirements() {
    log_info "Checking build requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Dockerfile exists
    if [[ ! -f "$DOCKERFILE_PATH" ]]; then
        log_error "Dockerfile not found: $DOCKERFILE_PATH"
        exit 1
    fi
    
    # Check build context
    if [[ ! -d "$BUILD_CONTEXT" ]]; then
        log_error "Build context directory not found: $BUILD_CONTEXT"
        exit 1
    fi
    
    log_success "All requirements satisfied"
}

# Build the Docker image
build_image() {
    log_info "Building CPU-only Docker image..."
    log_info "Image: $DOCKER_TAG"
    log_info "Dockerfile: $DOCKERFILE_PATH"
    log_info "Context: $BUILD_CONTEXT"
    
    # Construct build command
    local build_cmd="docker build"
    
    # Add BuildKit if enabled
    if [[ "$USE_BUILDKIT" == "1" ]]; then
        export DOCKER_BUILDKIT=1
        log_info "Using Docker BuildKit"
    fi
    
    # Add build arguments
    build_cmd="$build_cmd -f $DOCKERFILE_PATH"
    build_cmd="$build_cmd -t $DOCKER_TAG"
    build_cmd="$build_cmd --build-arg VARIANT=cpu"
    build_cmd="$build_cmd $USE_CACHE"
    
    # Add build-time variables
    if [[ -n "${BUILD_THREADS:-}" ]]; then
        build_cmd="$build_cmd --build-arg BUILD_THREADS=$BUILD_THREADS"
    fi
    
    if [[ -n "${TARGET_ARCH:-}" ]]; then
        build_cmd="$build_cmd --build-arg TARGET_ARCH=$TARGET_ARCH"
    fi
    
    # Add context
    build_cmd="$build_cmd $BUILD_CONTEXT"
    
    # Execute or show command
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN - Would execute:"
        echo "$build_cmd"
        return 0
    fi
    
    log_info "Executing: $build_cmd"
    if eval "$build_cmd"; then
        log_success "Docker image built successfully: $DOCKER_TAG"
    else
        log_error "Docker build failed"
        exit 1
    fi
}

# Validate the built image
validate_image() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Validating built image..."
    
    # Check image exists
    if ! docker image inspect "$DOCKER_TAG" &> /dev/null; then
        log_error "Built image not found: $DOCKER_TAG"
        exit 1
    fi
    
    # Test container startup
    log_info "Testing container startup..."
    if ! docker run --rm "$DOCKER_TAG" python --version; then
        log_error "Container failed to start or Python not available"
        exit 1
    fi
    
    # Test MCTS module import
    log_info "Testing MCTS module import..."
    if ! docker run --rm "$DOCKER_TAG" python -c "from corridors.corridors_mcts import Corridors_MCTS; print('MCTS module loaded successfully')"; then
        log_warning "MCTS module import failed - this may be expected if module not built yet"
    fi
    
    # Show image information
    log_info "Image information:"
    docker image inspect "$DOCKER_TAG" --format "Size: {{.Size}} bytes"
    docker image inspect "$DOCKER_TAG" --format "Created: {{.Created}}"
    
    log_success "Image validation completed"
}

# Push image if requested
push_image() {
    if [[ "$PUSH_IMAGE" != "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Pushing image to registry..."
    if docker push "$DOCKER_TAG"; then
        log_success "Image pushed successfully: $DOCKER_TAG"
    else
        log_error "Failed to push image"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    if [[ "$VERBOSE" == "true" ]]; then
        set +x
    fi
}

# Main execution
main() {
    trap cleanup EXIT
    
    log_info "Starting CPU-only Docker build"
    log_info "Project: MCTS Corridors Game"
    
    check_requirements
    build_image
    validate_image
    push_image
    
    log_success "CPU build completed successfully!"
    log_info "Image: $DOCKER_TAG"
    
    # Show usage examples
    cat << EOF

Usage Examples:
    # Run interactive container
    docker run -it --rm $DOCKER_TAG /bin/bash
    
    # Run MCTS simulation
    docker run --rm $DOCKER_TAG python -c "
from corridors.corridors_mcts import Corridors_MCTS
mcts = Corridors_MCTS(c=1.41, seed=42, min_simulations=100, max_simulations=1000)
print('MCTS ready for CPU-only execution')
"
    
    # Mount local code for development
    docker run -it --rm -v \$(pwd):/workspace -w /workspace $DOCKER_TAG /bin/bash

EOF
}

# Execute main function
main "$@"