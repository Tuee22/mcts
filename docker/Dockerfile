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

# Container runs as root for simplicity and cross-platform compatibility

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
    PATH="/usr/local/bin:${PATH}" \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PYTHONPATH="/app/backend/python:/opt/mcts/backend-build" \
    PYTHONDONTWRITEBYTECODE=1 \
    NPM_CONFIG_YES=true \
    NODE_PATH="/opt/mcts/frontend-build/node_modules" \
    DOCKER_CONTAINER=1

WORKDIR /app

# Create directories for build artifacts outside /app
RUN mkdir -p /opt/mcts/backend-build \
             /opt/mcts/frontend-build

# Install system dependencies - same for both CPU and CUDA since both use Ubuntu 22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git wget gpg gpg-agent xz-utils \
      software-properties-common build-essential pkg-config cmake \
      file \
      tini \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
      python3.12 python3.12-dev python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS for frontend E2E tests (works on both ARM64 and AMD64)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node --version && npm --version \
    && rm -rf /var/lib/apt/lists/*

# Install global NPM packages for frontend testing using versioned constraints
COPY frontend/npm-global-packages.json /tmp/npm-global-packages.json
RUN PACKAGES=$(node -e "const pkg = require('/tmp/npm-global-packages.json'); console.log(Object.entries(pkg.packages).map(([name, version]) => \`\${name}@\${version}\`).join(' '))") \
    && npm install -g $PACKAGES \
    && vitest --version \
    && rm /tmp/npm-global-packages.json

# Install Playwright system dependencies as root first
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnspr4 libnss3 libatk1.0-0 libatspi2.0-0 libx11-6 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libxcb1 \
    libxkbcommon0 libasound2 libgtk-3-0 libdrm2 libxss1 libglib2.0-0 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python3-config python3-config /usr/bin/python3.12-config 100 \
    && update-alternatives --install /usr/bin/python-config python-config /usr/bin/python3.12-config 100

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip and install base tools
RUN python -m pip install --upgrade pip wheel setuptools poetry

# Container runs as root - no user creation needed

# Copy dependency files first for better layer caching
COPY pyproject.toml /app/

# Install Python dependencies (without root package)
RUN poetry install --no-root --with dev

# Install Playwright system dependencies as root using official command
RUN poetry run playwright install-deps

# Build frontend during image construction (outside /app)
WORKDIR /opt/mcts/frontend-build
ENV CI=false
ENV GENERATE_SOURCEMAP=false
# Copy frontend source files for building
COPY frontend/package.json frontend/tsconfig.json ./
COPY frontend/src ./src
COPY frontend/public ./public
# Install dependencies and build to current directory
# Note: npm install used instead of npm ci because package-lock.json is intentionally excluded
# This ensures cross-platform compatibility and .dockerignore prevents artifacts from entering build context
RUN npm install --no-audit --no-fund && npm run build

# Copy source code to /app (git-versioned files only)
COPY . /app

# Install the root package (for scripts) as root
WORKDIR /app
RUN poetry install --with dev

# Build C++ backend during image construction (to /opt/mcts/backend-build)
WORKDIR /app/backend/core

# Verify user permissions and prepare build environment
RUN echo "=== Permission Check ===" && id && whoami && \
    echo "=== Build Directory Setup ===" && ls -la /opt/mcts/backend-build/

# Build C++ extension to external directory
RUN scons target=/opt/mcts/backend-build/_corridors_mcts

# Verify builds completed successfully
WORKDIR /app
RUN ls -la /opt/mcts/frontend-build/build/index.html && echo "✅ Frontend build completed"
RUN python -c "import sys; sys.path.insert(0, '/opt/mcts/backend-build'); import _corridors_mcts; print('✅ Backend build completed:', _corridors_mcts.__file__)"

# ──────────────────────────────────────────────────────────────────────────────
# In CUDA builds (FROM nvidia/cuda:... images), the base image automatically
# configures NVIDIA's official CUDA APT repository inside /etc/apt/sources.list.d
# and /etc/apt/trusted.gpg.d. This repo is only needed if you plan to install
# *additional* CUDA packages (e.g., cudnn, nccl, tensorrt, toolkit components)
# at build time via `apt-get install ...`.
#
# For our use case:
#   - The CUDA runtime libraries are already baked into the base image.
#   - We are *not* installing any additional CUDA packages via apt.
#   - The host NVIDIA driver is provided at runtime by the NVIDIA Container Toolkit.
#
# Problem:
#   - Playwright’s `install-deps` command internally calls `apt-get update`.
#   - When `apt-get update` hits NVIDIA’s repo, builds can fail due to transient
#     mirror inconsistencies (hash/size mismatches in Packages.gz).
#   - This introduces unnecessary fragility into CI/CD pipelines and local builds.
#
# Solution:
#   - For CUDA builds, we proactively *remove* the CUDA repo definitions and GPG
#     keys before running `playwright install-deps`.
#   - This ensures `apt-get update` only queries Ubuntu + NodeSource repos,
#     avoiding flaky NVIDIA mirrors entirely.
#   - If in the future you need to install CUDA packages via apt, simply remove
#     this block and re-enable the repo, or add it back explicitly.
#
# Multi-arch safety:
#   - The condition checks `$VARIANT`. On CPU/ARM builds (Ubuntu base image),
#     no CUDA repo exists → the `rm -f` is a no-op.
#   - On CUDA builds, the repo files are removed.
# ──────────────────────────────────────────────────────────────────────────────
RUN if [ "$VARIANT" = "cuda" ]; then \
      rm -f /etc/apt/sources.list.d/cuda*.list /etc/apt/trusted.gpg.d/nvidia*.gpg || true; \
    fi

# Official Playwright command to install system dependencies
RUN poetry run playwright install-deps
# Install all three browser engines for comprehensive E2E testing
RUN poetry run playwright install chromium firefox webkit
# Verify Playwright browsers are installed correctly
RUN ls -la /root/.cache/ms-playwright 2>/dev/null || echo "Playwright cache not found" && echo "✅ Playwright installation completed"

# Expose only the single server port
EXPOSE 8000

# Use tini for simple server startup (no JIT building)
ENTRYPOINT ["/usr/bin/tini", "--", "poetry", "run", "server"]