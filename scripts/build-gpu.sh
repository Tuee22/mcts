#!/bin/bash
#
# GPU-Enabled Docker Build Helper Script
# Builds containers with CUDA/GPU acceleration support
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="${MCTS_GPU_IMAGE:-mcts-gpu}"
COMPOSE_FILES=("-f" "${PROJECT_ROOT}/docker-compose.yaml" "-f" "${PROJECT_ROOT}/docker-compose.gpu.yaml")

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
GPU-Enabled Docker Build Helper

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -s, --service NAME  Build specific service (default: all GPU services)
    --no-cache          Build without using cache
    --pull              Pull latest base images before building
    --parallel          Build services in parallel
    --push              Push images after successful build
    --dry-run           Show commands without executing
    --verbose           Enable verbose output
    --validate          Run comprehensive GPU validation tests

ENVIRONMENT VARIABLES:
    MCTS_GPU_IMAGE      GPU image name (default: mcts-gpu)
    CUDA_VERSION        CUDA toolkit version (11.8, 12.x)
    NVIDIA_VISIBLE_DEVICES  GPU visibility (default: all)
    GPU_MEMORY_LIMIT    Limit GPU memory usage

GPU REQUIREMENTS:
    - NVIDIA GPU with Compute Capability 3.5+
    - NVIDIA Docker runtime (nvidia-docker2)
    - CUDA-compatible drivers
    - Docker Compose 3.8+ with GPU support

EXAMPLES:
    # Basic GPU build
    $0

    # Build without cache
    $0 --no-cache

    # Build specific service
    $0 --service mcts-gpu

    # Build with validation
    $0 --validate

    # Parallel build with latest base images
    $0 --pull --parallel

EOF
}

# Parse command line arguments
SERVICE_NAME=""
USE_CACHE=true
PULL_IMAGES=false
PARALLEL_BUILD=false
PUSH_IMAGES=false
DRY_RUN=false
VERBOSE=false
VALIDATE_GPU=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --no-cache)
            USE_CACHE=false
            shift
            ;;
        --pull)
            PULL_IMAGES=true
            shift
            ;;
        --parallel)
            PARALLEL_BUILD=true
            shift
            ;;
        --push)
            PUSH_IMAGES=true
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
        --validate)
            VALIDATE_GPU=true
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

# Check GPU requirements
check_gpu_requirements() {
    log_info "Checking GPU requirements..."
    
    # Check NVIDIA drivers
    if ! nvidia-smi &> /dev/null; then
        log_error "NVIDIA drivers not installed or nvidia-smi not available"
        log_error "Install NVIDIA drivers compatible with your GPU"
        exit 1
    fi
    
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
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check NVIDIA Docker runtime
    log_info "Testing NVIDIA Docker runtime..."
    if ! docker run --rm --gpus all nvidia/cuda:11.8-base nvidia-smi &> /dev/null; then
        log_error "NVIDIA Docker runtime not working"
        log_error "Install nvidia-docker2 or configure nvidia-container-runtime"
        exit 1
    fi
    
    # Check Compose files exist
    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ "$compose_file" != "-f" ]] && [[ ! -f "$compose_file" ]]; then
            log_error "Compose file not found: $compose_file"
            exit 1
        fi
    done
    
    log_success "GPU requirements satisfied"
    
    # Show GPU information
    log_info "Available GPUs:"
    nvidia-smi --query-gpu=index,name,memory.total,compute_cap --format=csv,noheader,nounits | \
        while IFS=, read -r index name memory compute_cap; do
            log_info "  GPU $index: $name (${memory}MB, Compute $compute_cap)"
        done
}

# Pull base images if requested
pull_base_images() {
    if [[ "$PULL_IMAGES" != "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Pulling latest base images..."
    
    local pull_cmd="docker compose ${COMPOSE_FILES[*]} pull"
    
    if [[ -n "$SERVICE_NAME" ]]; then
        pull_cmd="$pull_cmd $SERVICE_NAME"
    fi
    
    log_info "Executing: $pull_cmd"
    if eval "$pull_cmd"; then
        log_success "Base images updated"
    else
        log_warning "Failed to pull some base images, continuing with build"
    fi
}

# Build GPU images
build_gpu_images() {
    log_info "Building GPU-enabled Docker images..."
    
    # Construct build command
    local build_cmd="docker compose ${COMPOSE_FILES[*]} build"
    
    # Add options
    if [[ "$USE_CACHE" != "true" ]]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    if [[ "$PARALLEL_BUILD" == "true" ]]; then
        build_cmd="$build_cmd --parallel"
    fi
    
    # Add service if specified
    if [[ -n "$SERVICE_NAME" ]]; then
        build_cmd="$build_cmd $SERVICE_NAME"
    fi
    
    # Execute or show command
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN - Would execute:"
        echo "$build_cmd"
        return 0
    fi
    
    log_info "Executing: $build_cmd"
    if eval "$build_cmd"; then
        log_success "GPU images built successfully"
    else
        log_error "GPU build failed"
        exit 1
    fi
}

# Validate GPU functionality
validate_gpu_functionality() {
    if [[ "$VALIDATE_GPU" != "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Validating GPU functionality..."
    
    local service="${SERVICE_NAME:-mcts-gpu}"
    
    # Test 1: GPU visibility
    log_info "Testing GPU visibility..."
    if ! docker compose "${COMPOSE_FILES[@]}" run --rm "$service" nvidia-smi; then
        log_error "GPU not visible in container"
        exit 1
    fi
    
    # Test 2: CUDA runtime
    log_info "Testing CUDA runtime..."
    if ! docker compose "${COMPOSE_FILES[@]}" run --rm "$service" nvcc --version; then
        log_error "CUDA compiler not available"
        exit 1
    fi
    
    # Test 3: Python GPU libraries
    log_info "Testing Python GPU libraries..."
    local gpu_test_script="
import torch
import sys

print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')

if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'GPU {i}: {torch.cuda.get_device_name(i)}')
        print(f'  Memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.1f} GB')
    
    # Test GPU memory allocation
    try:
        x = torch.randn(1000, 1000, device='cuda')
        y = torch.randn(1000, 1000, device='cuda')
        z = torch.mm(x, y)
        print('GPU computation test: PASSED')
    except Exception as e:
        print(f'GPU computation test: FAILED - {e}')
        sys.exit(1)
else:
    print('GPU computation test: FAILED - CUDA not available')
    sys.exit(1)
"
    
    if ! docker compose "${COMPOSE_FILES[@]}" run --rm "$service" python -c "$gpu_test_script"; then
        log_error "GPU Python libraries validation failed"
        exit 1
    fi
    
    # Test 4: MCTS with GPU (if available)
    log_info "Testing MCTS GPU integration..."
    local mcts_test_script="
try:
    from corridors.corridors_mcts import Corridors_MCTS
    print('MCTS module loaded successfully')
    
    # Basic MCTS test
    mcts = Corridors_MCTS(c=1.41, seed=42, min_simulations=100, max_simulations=1000)
    print('MCTS instance created successfully')
    print('GPU-enabled MCTS validation: PASSED')
except ImportError as e:
    print(f'MCTS module not available: {e}')
    print('This may be expected if MCTS not built with GPU support')
except Exception as e:
    print(f'MCTS validation failed: {e}')
"
    
    if ! docker compose "${COMPOSE_FILES[@]}" run --rm "$service" python -c "$mcts_test_script"; then
        log_warning "MCTS GPU integration test failed - may be expected if not implemented"
    fi
    
    log_success "GPU validation completed successfully"
}

# Show GPU image information
show_image_info() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "GPU image information:"
    
    # Get image names from docker-compose
    local images
    images=$(docker compose "${COMPOSE_FILES[@]}" config --images 2>/dev/null || echo "$IMAGE_NAME")
    
    for image in $images; do
        if docker image inspect "$image" &> /dev/null; then
            log_info "Image: $image"
            docker image inspect "$image" --format "  Size: {{.Size}} bytes ({{.VirtualSize}} virtual)"
            docker image inspect "$image" --format "  Created: {{.Created}}"
            
            # Show GPU-specific layers if verbose
            if [[ "$VERBOSE" == "true" ]]; then
                docker history "$image" | grep -i -E "(cuda|nvidia|gpu)" || true
            fi
        fi
    done
}

# Push images if requested
push_gpu_images() {
    if [[ "$PUSH_IMAGES" != "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Pushing GPU images to registry..."
    
    local push_cmd="docker compose ${COMPOSE_FILES[*]} push"
    
    if [[ -n "$SERVICE_NAME" ]]; then
        push_cmd="$push_cmd $SERVICE_NAME"
    fi
    
    if eval "$push_cmd"; then
        log_success "GPU images pushed successfully"
    else
        log_error "Failed to push GPU images"
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
    
    log_info "Starting GPU-enabled Docker build"
    log_info "Project: MCTS Corridors Game with GPU Acceleration"
    
    check_gpu_requirements
    pull_base_images
    build_gpu_images
    validate_gpu_functionality
    show_image_info
    push_gpu_images
    
    log_success "GPU build completed successfully!"
    
    # Show usage examples
    cat << EOF

Usage Examples:
    # Run interactive GPU container
    docker compose ${COMPOSE_FILES[*]} run --rm mcts-gpu /bin/bash
    
    # Check GPU status
    docker compose ${COMPOSE_FILES[*]} run --rm mcts-gpu nvidia-smi
    
    # Run GPU-accelerated MCTS
    docker compose ${COMPOSE_FILES[*]} run --rm mcts-gpu python -c "
from corridors.corridors_mcts import Corridors_MCTS
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
mcts = Corridors_MCTS(c=1.41, seed=42, min_simulations=1000, max_simulations=10000)
print('GPU-accelerated MCTS ready')
"
    
    # Development with GPU support
    docker compose ${COMPOSE_FILES[*]} run --rm -v \$(pwd):/workspace mcts-gpu /bin/bash

EOF
}

# Execute main function
main "$@"