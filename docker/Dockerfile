# syntax=docker/dockerfile:1.6

# Multi-stage build with TARGET support
ARG TARGET=cpu

# -------- Base stages --------
FROM ubuntu:22.04 AS base-cpu
FROM nvidia/cuda:12.6.2-devel-ubuntu22.04 AS base-cuda
FROM ubuntu:22.04 AS base-arm

# Select the appropriate base stage
FROM base-${TARGET} AS final

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:${PATH}" \
    CI=1 \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

WORKDIR /app

# ---- System deps: Python, Poetry, Node, build tooling ----
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git build-essential pkg-config make tini \
      python3 python3-dev python3-venv python3-pip \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Remove system blinker packages to prevent conflicts
RUN apt-get update && apt-get purge -y python3-blinker python3-blinker-doc || true \
    && rm -rf /usr/lib/python3/dist-packages/blinker* || true \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Install deps without relying on lock file ----
COPY pyproject.toml /app/
RUN poetry install --with dev --no-root --no-interaction --no-ansi

# ---- Copy the rest of the repo and install the root package (scripts) ----
COPY . /app
RUN poetry install --with dev --no-interaction --no-ansi

# ---- Build C++ extension using SCons ----
WORKDIR /app/backend/core
RUN scons

# ---- Verify extension was built ----
RUN ls -la /app/backend/python/corridors/_corridors_mcts.so && echo "✅ Extension built successfully"

# Optional: some code expects this symlink for static assets
WORKDIR /app
RUN mkdir -p /home/mcts && ln -s /app/frontend /home/mcts/frontend || true

# Start API server directly
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-m", "backend.api.server"]