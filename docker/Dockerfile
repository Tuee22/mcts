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

# ---- System deps: Build tools first ----
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git build-essential pkg-config make tini \
      software-properties-common gpg gpg-agent \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Install Python 3.12 from deadsnakes PPA ----
RUN add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
      python3.12 python3.12-dev python3.12-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Remove system Python packages that conflict and set up Python 3.12 as default ----
RUN apt-get update \
    && apt-get remove -y python3-blinker python3-blinker-doc || true \
    && apt-get autoremove -y \
    && rm -rf /usr/lib/python3/dist-packages/blinker* \
    && rm -rf /usr/lib/python3.10/dist-packages/blinker* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Install pip and Poetry for Python 3.12 ----
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 \
    && python3.12 -m pip install --upgrade pip setuptools wheel \
    && curl -sSL https://install.python-poetry.org | python3.12 - \
    && python3.12 -m pip install --force-reinstall --no-deps blinker

# ---- Install Node.js ----
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
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

# Optional: some code expects this syml for static assets
WORKDIR /app
RUN mkdir -p /home/mcts && ln -s /app/frontend /home/mcts/frontend || true

# Start API server directly
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "backend.api.server"]