---
name: builder-gpu
description: Build GPU-enabled Docker containers when GPU support is available and configured
---

# GPU-Enabled Docker Builder Agent

**Agent Name**: @builder-gpu  
**Purpose**: Build Docker containers with GPU acceleration support  
**Command**: `docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build`

## Overview

This agent builds Docker containers with full GPU support, including CUDA libraries, GPU-accelerated computing libraries, and NVIDIA container runtime integration. Designed for high-performance MCTS computations and GPU-accelerated machine learning workloads.

## When to Use

- **Performance Computing**: GPU-accelerated MCTS simulations
- **Machine Learning**: Neural network training and inference
- **Production Deployment**: High-throughput GPU servers
- **Benchmarking**: Performance comparison against CPU implementations
- **Research**: GPU-optimized algorithm development

## System Requirements

### Hardware Prerequisites
- **NVIDIA GPU**: Compatible GPU with CUDA Compute Capability 3.5+
- **Memory**: 8GB+ system RAM, 4GB+ GPU memory
- **Storage**: 10GB+ available disk space for GPU images

### Software Prerequisites
- **Docker**: Version 19.03+ with GPU support
- **NVIDIA Docker**: `nvidia-docker2` or Docker 19.03+ with `nvidia-container-runtime`
- **NVIDIA Drivers**: Compatible drivers for target CUDA version
- **Docker Compose**: Version 3.8+ for GPU service definitions

## Operating Procedures

### 1. Pre-Build System Validation
```bash
# Verify NVIDIA drivers
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-base nvidia-smi

# Validate Docker Compose version
docker compose version

# Check available GPU memory
nvidia-ml-py3 -i
```

### 2. Build Process

#### Standard Build Process
```bash
# Primary GPU build command
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build

# Build specific service
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build mcts-gpu

# Pull latest base images first
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml pull
```

#### Dependency Change Build Process (CRITICAL for pyproject.toml changes)
```bash
# MANDATORY: Clean build when dependencies change
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build --no-cache

# Multi-CUDA architecture build (test all supported GPU generations)
docker build -f docker/Dockerfile.gpu \
  --build-arg CUDA_ARCHITECTURES="70;75;80;86;89;90" \
  --no-cache \
  -t mcts-gpu:multi-arch .

# Test builds for different CUDA versions
docker build -f docker/Dockerfile.gpu \
  --build-arg CUDA_VERSION=11.8 \
  --build-arg CUDNN_VERSION=8 \
  --no-cache \
  -t mcts-gpu:cuda118 .

docker build -f docker/Dockerfile.gpu \
  --build-arg CUDA_VERSION=12.1 \
  --build-arg CUDNN_VERSION=8 \
  --no-cache \
  -t mcts-gpu:cuda121 .
```

### 3. GPU Runtime Validation

#### Standard GPU Validation
```bash
# Test GPU container startup
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu nvidia-smi

# Validate CUDA installation
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu nvcc --version

# Test Python GPU libraries
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu \
  python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

#### Comprehensive GPU Architecture Validation (REQUIRED for dependency changes)
```bash
# Test multi-architecture GPU support
docker run --rm --gpus all mcts-gpu:multi-arch nvidia-smi
docker run --rm --gpus all mcts-gpu:multi-arch nvcc --version

# Validate CUDA versions
docker run --rm --gpus all mcts-gpu:cuda118 python -c "import torch; print(f'CUDA 11.8 - Available: {torch.cuda.is_available()}, Version: {torch.version.cuda}')"
docker run --rm --gpus all mcts-gpu:cuda121 python -c "import torch; print(f'CUDA 12.1 - Available: {torch.cuda.is_available()}, Version: {torch.version.cuda}')"

# Test GPU memory and compute capabilities
docker run --rm --gpus all mcts-gpu:multi-arch python -c "
import torch
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f'GPU {i}: {props.name}, Compute: {props.major}.{props.minor}, Memory: {props.total_memory/1024**3:.1f}GB')
else:
    print('No GPUs detected')
"

# Validate all dependency imports work with GPU
docker run --rm --gpus all mcts-gpu:multi-arch python -c "
import pytest, playwright, torch, numpy as np
print('All dependencies imported successfully with GPU support')
print(f'PyTorch CUDA: {torch.cuda.is_available()}')
print(f'GPU Count: {torch.cuda.device_count()}')
"
```

### 4. MCTS GPU Integration Testing
```bash
# Test MCTS with GPU acceleration
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu \
  python -c "from corridors.corridors_mcts import Corridors_MCTS; print('MCTS GPU ready')"

# Run GPU performance benchmark
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu \
  python -m pytest tests/performance/ -k gpu
```

## Build Configuration

### GPU Docker Compose Override
The `docker-compose.gpu.yaml` file should include:

```yaml
version: "3.8"
services:
  mcts-gpu:
    build:
      context: .
      dockerfile: docker/Dockerfile.gpu
      args:
        CUDA_VERSION: "11.8"
        CUDNN_VERSION: "8"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### CUDA Version Management
- **CUDA 11.8**: Recommended for broad compatibility
- **CUDA 12.x**: Latest features but may have compatibility issues
- **Multi-CUDA**: Support multiple CUDA versions if needed

### GPU Memory Management
- **Memory Allocation**: Configure GPU memory limits
- **Multi-GPU**: Support for multiple GPU setups
- **Memory Monitoring**: Tools for GPU memory usage tracking

## Environment Variables

### GPU Configuration
- `MCTS_GPU_BUILD_CMD`: Override default GPU build command
- `CUDA_VERSION`: Specify CUDA toolkit version
- `NVIDIA_VISIBLE_DEVICES`: Control GPU visibility
- `NVIDIA_DRIVER_CAPABILITIES`: Set driver capabilities

### Performance Tuning
- `GPU_MEMORY_FRACTION`: Limit GPU memory usage
- `CUDA_LAUNCH_BLOCKING`: Enable synchronous CUDA calls for debugging
- `PYTORCH_CUDA_ALLOC_CONF`: PyTorch GPU memory configuration

## Architecture and Platform Support

### Supported Platforms
- **Linux x86_64**: Primary target platform
- **AMD64 only**: GPU containers not supported on ARM64

### NVIDIA GPU Architectures
- **Pascal**: GTX 10xx series (Compute Capability 6.x)
- **Turing**: RTX 20xx series (Compute Capability 7.5)
- **Ampere**: RTX 30xx, A100 series (Compute Capability 8.x)
- **Ada Lovelace**: RTX 40xx series (Compute Capability 8.9)

## Performance Optimization

### GPU-Specific Optimizations
- **Tensor Cores**: Utilize mixed-precision computing
- **CUDA Streams**: Asynchronous GPU operations
- **Memory Coalescing**: Optimize memory access patterns
- **Kernel Fusion**: Combine multiple operations

### Library Optimizations
- **cuDNN**: GPU-accelerated deep learning primitives
- **cuBLAS**: GPU-accelerated linear algebra
- **Thrust**: GPU-accelerated parallel algorithms
- **CuPy**: NumPy-compatible GPU arrays

## Quality Assurance

### Functional Tests
1. **GPU Detection**: Verify all GPUs are visible and accessible
2. **CUDA Runtime**: Test CUDA kernel execution
3. **Memory Allocation**: Validate GPU memory allocation/deallocation
4. **Multi-GPU**: Test multi-GPU configurations if applicable

### Performance Benchmarks
1. **MCTS Simulations**: GPU vs CPU performance comparison
2. **Memory Bandwidth**: GPU memory throughput tests
3. **Compute Throughput**: FLOPS measurement and optimization
4. **Power Efficiency**: Performance per watt analysis

### Integration Testing
1. **Python Bindings**: GPU-accelerated C++ extensions
2. **Framework Compatibility**: PyTorch, TensorFlow, CuPy integration
3. **Container Orchestration**: Kubernetes GPU scheduling
4. **Multi-Container**: GPU sharing and isolation

## Monitoring and Debugging

### GPU Monitoring Tools
```bash
# Real-time GPU monitoring
nvidia-smi -l 1

# Detailed GPU information
nvidia-ml-py3

# GPU memory usage
gpustat

# CUDA profiling
nvprof python script.py
```

### Debug Commands
```bash
# Verbose build with GPU details
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build --progress=plain

# Interactive GPU debugging
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm -it mcts-gpu /bin/bash

# GPU memory debugging
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml run --rm mcts-gpu \
  python -c "import torch; print(torch.cuda.memory_summary())"
```

## Common Issues and Solutions

### Build Issues
1. **CUDA Version Mismatch**: Ensure driver compatibility with CUDA version
2. **Base Image Pull Failure**: Check access to NVIDIA container registry
3. **Compilation Errors**: Verify compute capability and nvcc flags
4. **Memory Limits**: Increase Docker memory allocation for GPU builds

### Runtime Issues
1. **GPU Not Detected**: Check nvidia-docker installation and permissions
2. **CUDA Out of Memory**: Implement GPU memory management strategies
3. **Driver Compatibility**: Update NVIDIA drivers or downgrade CUDA
4. **Performance Issues**: Profile GPU usage and optimize kernels

### Debugging Checklist
- [ ] NVIDIA drivers installed and functional (`nvidia-smi`)
- [ ] Docker has GPU support enabled
- [ ] Container runtime configured for GPU access
- [ ] CUDA version compatible with drivers
- [ ] GPU memory available and not oversubscribed
- [ ] Application properly utilizing GPU resources

## Success Criteria

### Build Success
- ✅ Docker GPU image builds without errors
- ✅ All GPU services start successfully
- ✅ NVIDIA SMI accessible from container
- ✅ CUDA runtime functional and version correct
- ✅ GPU memory allocation working

### Performance Validation
- ✅ GPU utilization > 70% during MCTS simulations
- ✅ Significant speedup over CPU-only implementation
- ✅ Memory transfer efficiency optimized
- ✅ Multi-GPU scaling if applicable
- ✅ Thermal management within acceptable limits

## Security Considerations

### GPU Access Controls
- Limit GPU device exposure to necessary containers only
- Use resource limits to prevent GPU memory exhaustion
- Monitor GPU usage for unauthorized access patterns
- Implement container security scanning for GPU images

### Network Security
- Secure GPU cluster communication
- Encrypted data transfer for distributed GPU workloads
- Access controls for GPU management interfaces
- Container isolation for multi-tenant GPU usage

## Related Agents

- **@builder-docker**: Standard Docker builds without GPU
- **@builder-cpu**: CPU-only optimized container builds
- **@tester-pytest**: Run GPU-accelerated test suites
- **@mypy-type-checker**: Type validation for GPU code paths