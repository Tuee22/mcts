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
    POETRY_HOME=/usr/local \
    CI=1 \
    PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# Install system dependencies - same for both CPU and CUDA since both use Ubuntu 22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git wget gpg gpg-agent xz-utils \
      software-properties-common build-essential pkg-config cmake scons \
      tini \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
      python3.12 python3.12-dev python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS for frontend E2E tests (works on both ARM64 and AMD64)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node --version && npm --version

# Install Playwright system dependencies for browser support
# Using playwright install-deps ensures all required libraries for all browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnspr4 libnss3 libatk1.0-0 libatspi2.0-0 libx11-6 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libxcb1 \
    libxkbcommon0 libasound2 libgtk-3-0 libdrm2 libxss1 libglib2.0-0 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python3-config python3-config /usr/bin/python3.12-config 100

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip and install base tools
RUN python3 -m pip install --upgrade pip wheel setuptools poetry

# Create user with matching UID/GID for development
RUN groupadd -g ${GROUP_ID} ${USERNAME} 2>/dev/null || true \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ${USERNAME} 2>/dev/null || true \
    && mkdir -p /home/${USERNAME} \
    && chown -R ${USER_ID}:${GROUP_ID} /app /home/${USERNAME}

# Copy dependency files first for better layer caching
COPY pyproject.toml /app/

# Install Python dependencies (without root package)
RUN poetry install --no-root --with dev

# Copy the entire project
COPY . /app

# Install the root package (for scripts) as root
RUN poetry install --with dev

# Build frontend during image creation (deferred to runtime if it fails)
RUN cd frontend \
    && npm cache clean --force \
    && (npm ci || npm install) \
    && npm run build \
    && echo "✅ Frontend build complete" \
    || echo "⚠️ Frontend build failed - will retry at runtime"

# Install Playwright system dependencies only (not browsers yet)
# Must be done as root for system-wide installation
RUN playwright install-deps

# Build C++ during image creation (changed from skipping to building)
WORKDIR /app/backend/core
# Skip C++ build on AMD64 due to emulation limitations causing segfaults
RUN if [ "$(arch)" = "aarch64" ]; then scons -c && scons -Q; else echo "Skipping C++ build on $(arch) due to emulation"; fi

# Copy entrypoint script and make executable (before switching to user)
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Fix ownership of all built files
RUN chown -R ${USER_ID}:${GROUP_ID} /app

# Switch to user for runtime
USER ${USER_ID}:${GROUP_ID}

# Verify scons is available for runtime build
RUN which scons && echo "✅ SCons available for runtime build"

# Create symlink for static assets (optional, soft fail)
WORKDIR /app

# Expose only the single server port
EXPOSE 8000

# Use tini for proper signal handling with our entrypoint script
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]