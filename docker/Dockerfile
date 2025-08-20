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

# User arguments for development
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=mcts

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
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip and install base tools
RUN python3 -m pip install --upgrade pip wheel setuptools

# Install Poetry from official installer and make it globally accessible
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && cp /root/.local/bin/poetry /usr/local/bin/poetry \
    && chmod +x /usr/local/bin/poetry

# Create user with matching UID/GID for development
RUN groupadd -g ${GROUP_ID} ${USERNAME} 2>/dev/null || true \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ${USERNAME} 2>/dev/null || true \
    && mkdir -p /home/${USERNAME} \
    && chown -R ${USER_ID}:${GROUP_ID} /app /home/${USERNAME}

# Copy dependency files first for better layer caching
COPY pyproject.toml /app/

# Install Python dependencies (without root package)
RUN poetry install --no-root --with dev --without ml,data,viz,cuda

# Copy the entire project
COPY . /app

# Install the root package (for scripts) as root
RUN poetry install --with dev --without ml,data,viz,cuda

# Skip C++ build during image creation - will be built on container start
# This ensures the module is compiled for the runtime architecture
WORKDIR /app/backend/core

# Fix ownership of all built files
RUN chown -R ${USER_ID}:${GROUP_ID} /app

# Switch to user for runtime
USER ${USER_ID}:${GROUP_ID}

# Verify scons is available for runtime build
RUN which scons && echo "✅ SCons available for runtime build"

# Create symlink for static assets (optional, soft fail)
WORKDIR /app
RUN mkdir -p /home/mcts && ln -s /app/frontend /home/mcts/frontend || true

# Expose API port
EXPOSE 8000

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - clean and rebuild C++ to ensure correct architecture, then launch backend API server
CMD ["sh", "-c", "cd /app/backend/core && scons -c -Q && scons -Q && cd /app && exec python -m backend.api.server"]
