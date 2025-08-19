# syntax=docker/dockerfile:1.6

# Build arguments must be defined before FROM to use in FROM
ARG VARIANT=cpu
ARG CPU_BASE=ubuntu:22.04
ARG CUDA_BASE=nvidia/cuda:12.6.2-devel-ubuntu22.04
ARG BASE_IMAGE=${CPU_BASE}

# Use the selected base image
FROM ${BASE_IMAGE}

# Pass VARIANT through for use after FROM
ARG VARIANT
ARG TARGETARCH
ARG DEBIAN_FRONTEND=noninteractive

# Fast-fail: forbid CUDA on non-amd64
RUN set -eux; if [ "$VARIANT" = "cuda" ] && [ "$TARGETARCH" != "amd64" ]; then \
      echo "Error: CUDA variant requires amd64 architecture (got ${TARGETARCH})" >&2; exit 1; fi

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    CI=1 \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install system dependencies - same for both CPU and CUDA since both use Ubuntu 22.04
RUN --mount=type=cache,target=/var/cache/apt,id=mcts-apt-${VARIANT} \
    --mount=type=cache,target=/var/lib/apt/lists,id=mcts-aptlists-${VARIANT} \
    apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git wget gpg gpg-agent \
      software-properties-common build-essential pkg-config cmake scons \
      tini \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
      python3.12 python3.12-dev python3.12-venv \
      libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Install Poetry
RUN python3 -m pip install "poetry>=1.7"

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* /app/

# Install Python dependencies (without root package)
RUN poetry install --no-root --with dev --without ml,data,viz,cuda

# Copy the entire project
COPY . /app

# Install the root package (for scripts)
RUN poetry install --with dev --without ml,data,viz,cuda

# Build C++ extension using SCons
WORKDIR /app/backend/core
RUN scons || echo "Warning: C++ build failed, continuing for development"

# Verify extension was built (soft fail for development)
RUN if [ -f /app/backend/python/corridors/_corridors_mcts.so ]; then \
      echo "✅ Extension built successfully"; \
    else \
      echo "⚠️  Extension not built, some tests may fail"; \
    fi

# Create symlink for static assets (optional, soft fail)
WORKDIR /app
RUN mkdir -p /home/mcts && ln -s /app/frontend /home/mcts/frontend || true

# Expose API port
EXPOSE 8000

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - show versions and wait
CMD ["bash", "-c", "poetry --version && python --version && echo 'MCTS container ready' && tail -f /dev/null"]