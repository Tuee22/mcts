ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH="/app:/app/backend/python"
ENV PATH="/root/.local/bin:$PATH"

# Update package lists
RUN apt update

# Install basic dependencies
RUN apt install -y curl wget git software-properties-common pkg-config tini

# Remove system blinker packages to prevent conflicts
RUN apt purge -y python3-blinker python3-blinker-doc || true
RUN rm -rf /usr/lib/python3/dist-packages/blinker* || true
RUN rm -rf /usr/lib/python3.10/dist-packages/blinker* || true

# Add deadsnakes PPA for Python 3.12
RUN add-apt-repository -y ppa:deadsnakes/ppa

# Add GCC 13 PPA
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test

# Update after adding PPAs
RUN apt update

# Install Python 3.12
RUN apt install -y python3.12 python3.12-dev python3.12-venv

# Install GCC 13
RUN apt install -y gcc-13 g++-13

# Install build tools
RUN apt install -y build-essential

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100

# Set Python as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 100

# Set GCC 13 as default
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100 --slave /usr/bin/g++ g++ /usr/bin/g++-13

# Install pip
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip
RUN python3.12 -m pip install --upgrade pip setuptools wheel

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3.12 -

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

# Install Node.js
RUN apt install -y nodejs

# Clean up
RUN apt clean
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project file
COPY pyproject.toml ./

# Install Python dependencies
RUN poetry install --with dev --no-interaction --no-root

# Copy source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY tests/ ./tests/

# Build C++ module
WORKDIR /app/backend/core
RUN scons
RUN cp _corridors_mcts.so ../python/corridors/

# Install frontend dependencies
WORKDIR /app/frontend
RUN npm install

# Build frontend
RUN npm run build

# Install frontend test dependencies
WORKDIR /app/tests/frontend
RUN npm install

# Final setup
WORKDIR /app
RUN poetry install --no-root

# Use tini as init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default to running the server
CMD ["python3", "-m", "backend.api.server"]