---
name: builder-cpu
description: Build CPU-only Docker containers to catch build and compile errors
---

# CPU-Only Docker Builder Agent

**Agent Name**: @builder-cpu  
**Purpose**: Build Docker containers optimized for CPU-only environments  
**Command**: `docker build -f docker/Dockerfile.cpu -t mcts-cpu .`

## Overview

This agent builds Docker containers specifically for CPU-only environments, excluding GPU dependencies and CUDA libraries. Ideal for development environments, CI/CD pipelines, and deployment targets without GPU hardware.

## When to Use

- **Development**: Local development on machines without GPU support
- **CI/CD**: Build validation in CPU-only pipeline runners
- **Deployment**: Production environments without GPU acceleration
- **Testing**: Validate core functionality without GPU dependencies
- **Resource Constraints**: Smaller image size for limited storage/bandwidth

## Operating Procedures

### 1. Pre-Build Validation
- Check Docker daemon availability: `docker info`
- Verify CPU Dockerfile exists: `docker/Dockerfile.cpu`
- Validate base image accessibility
- Check available disk space for build layers

### 2. Build Process

#### Standard Build
```bash
# Primary CPU build command
docker build -f docker/Dockerfile.cpu -t mcts-cpu .

# Alternative build with BuildKit (faster)
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile.cpu -t mcts-cpu .

# Build with build args if needed
docker build -f docker/Dockerfile.cpu \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg BUILD_TYPE=release \
  -t mcts-cpu .
```

#### Dependency Change Build (REQUIRED when pyproject.toml changes)
```bash
# CRITICAL: Always use --no-cache when dependencies change
docker build -f docker/Dockerfile.cpu --no-cache -t mcts-cpu .

# Multi-architecture build for dependency changes (MANDATORY)
docker buildx build --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile.cpu \
  --no-cache \
  -t mcts-cpu:latest .

# Test build on both architectures
docker buildx build --platform linux/amd64 \
  -f docker/Dockerfile.cpu \
  --no-cache \
  -t mcts-cpu:amd64 \
  --load .

docker buildx build --platform linux/arm64 \
  -f docker/Dockerfile.cpu \
  --no-cache \
  -t mcts-cpu:arm64 \
  --load .
```

### 3. Post-Build Validation

#### Standard Validation
- Verify image was created: `docker images mcts-cpu`
- Test container startup: `docker run --rm mcts-cpu python --version`
- Validate MCTS module loading: `docker run --rm mcts-cpu python -c "from corridors.corridors_mcts import Corridors_MCTS"`
- Check image size and layers: `docker inspect mcts-cpu`

#### Multi-Architecture Validation (REQUIRED for dependency changes)
```bash
# Test AMD64 build
docker run --rm --platform linux/amd64 mcts-cpu:amd64 python --version
docker run --rm --platform linux/amd64 mcts-cpu:amd64 python -c "import pytest, playwright; print('All dependencies available')"

# Test ARM64 build  
docker run --rm --platform linux/arm64 mcts-cpu:arm64 python --version
docker run --rm --platform linux/arm64 mcts-cpu:arm64 python -c "import pytest, playwright; print('All dependencies available')"

# Dependency validation for both architectures
docker run --rm --platform linux/amd64 mcts-cpu:amd64 python -c "from corridors.corridors_mcts import Corridors_MCTS; print('MCTS AMD64 OK')"
docker run --rm --platform linux/arm64 mcts-cpu:arm64 python -c "from corridors.corridors_mcts import Corridors_MCTS; print('MCTS ARM64 OK')"
```

### 4. Error Handling
- **Dockerfile not found**: Check `docker/Dockerfile.cpu` exists
- **Build context too large**: Add entries to `.dockerignore`
- **Base image pull failure**: Check network connectivity and registry access
- **Compilation errors**: Review C++ build dependencies and flags
- **Python import errors**: Verify all dependencies in requirements.txt

## Build Optimizations

### Image Size Reduction
- Multi-stage builds to exclude development tools
- Minimal base images (Alpine, distroless)
- Remove unnecessary packages after installation
- Use `.dockerignore` to exclude build artifacts

### Build Speed
- Layer caching strategy for dependencies
- BuildKit for parallel builds and improved caching
- Pre-built base images with common dependencies
- Efficient dependency installation order

### CPU-Specific Optimizations
- Enable CPU-specific compiler optimizations
- Remove GPU libraries and CUDA dependencies
- Optimize for target CPU architecture (x86_64, ARM64)
- Use CPU-optimized NumPy/SciPy builds

## Environment Variables

### Build Configuration
- `MCTS_CPU_BUILD_CMD`: Override default build command
- `DOCKER_BUILDKIT`: Enable BuildKit for enhanced builds
- `BUILD_TYPE`: Set to 'debug' or 'release'
- `TARGET_ARCH`: Specify target architecture

### Docker Build Args
- `PYTHON_VERSION`: Python version to use (default: 3.12)
- `BUILD_THREADS`: Number of compilation threads
- `OPTIMIZATION_LEVEL`: GCC optimization level (-O2, -O3)

## Quality Checks

### Functional Validation
1. **Python Environment**: Verify Python version and package installation
2. **MCTS Module**: Test C++ binding imports and basic functionality
3. **Dependencies**: Validate all required packages are available
4. **Performance**: Basic performance benchmarks for CPU execution

### Security Scanning
- Scan for vulnerabilities: `docker scan mcts-cpu`
- Check for exposed ports and services
- Validate user permissions and file ownership
- Review installed packages for security issues

## Architecture Support

### Primary Targets
- **x86_64 (AMD64)**: Primary development and deployment target
- **ARM64 (Apple Silicon)**: MacBook development and ARM servers

### Cross-Platform Builds
```bash
# Multi-platform build with buildx
docker buildx build --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile.cpu \
  -t mcts-cpu:latest .
```

## Integration with Main Pipeline

### Triggered By
- Changes to CPU-specific Dockerfile
- Build surface changes requiring CPU validation
- Explicit request for CPU-only testing
- CI/CD pipeline CPU validation stage

### Dependencies
- Docker daemon running
- Sufficient disk space (2GB+ recommended)
- Network access for base image and packages
- Build tools and compilers in Dockerfile

## Troubleshooting

### Common Issues
1. **Build Context Size**: Add more patterns to `.dockerignore`
2. **Memory Limits**: Increase Docker memory allocation
3. **Network Timeouts**: Check proxy settings and DNS resolution
4. **Permission Errors**: Verify Docker daemon permissions

### Debug Commands
```bash
# Verbose build output
docker build -f docker/Dockerfile.cpu --progress=plain -t mcts-cpu .

# Interactive debugging
docker run -it --rm mcts-cpu /bin/bash

# Layer-by-layer inspection
docker history mcts-cpu

# Build without cache
docker build --no-cache -f docker/Dockerfile.cpu -t mcts-cpu .
```

## Success Criteria

### Build Success
- ✅ Docker image created successfully
- ✅ Image tagged as `mcts-cpu:latest`
- ✅ Container starts without errors
- ✅ Python environment functional
- ✅ MCTS module imports successfully

### Performance Validation
- ✅ Basic MCTS simulation completes
- ✅ C++ bindings respond correctly
- ✅ Memory usage within expected bounds
- ✅ CPU utilization appropriate for workload

## Related Agents

- **@builder-docker**: Main Docker builder for development
- **@builder-gpu**: GPU-enabled container builds
- **@tester-pytest**: Test suite execution in containers
- **@mypy-type-checker**: Type validation before builds