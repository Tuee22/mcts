# Multi-architecture MCTS Docker image
# Supports: linux/amd64, linux/arm64
# For CUDA: use nvidia/cuda base image on amd64 only
ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# System update and base tools
RUN apt update && apt upgrade -y

# Install system dependencies
RUN apt install -y software-properties-common
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt update && apt install -y \
    gcc-13 g++-13 git curl wget valgrind cppcheck \
    libcairo2-dev pkg-config build-essential \
    python3-dev python3-distutils python3-setuptools \
    tini

# Install Node.js 20.x for React frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt install -y nodejs

# Configure GCC
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 1 --slave /usr/bin/g++ g++ /usr/bin/g++-13

# Install Python 3.12
RUN apt install -y python3.12 python3.12-venv python3.12-dev python3.12-lib2to3

# Configure Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
# Create python symlink for compatibility with npm packages
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3.12 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

WORKDIR /home

# Install project dependencies (lock file generated in container, not mounted)
COPY pyproject.toml ./
RUN python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); import distutils.util" && \
    find /usr/lib/python3/dist-packages -name "*blinker*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.12/dist-packages -name "*blinker*" -delete 2>/dev/null || true
RUN poetry install --with dev --no-interaction --no-root

# Copy all project files and set up environment
ENV PYTHONPATH="/home/mcts/:/home/mcts/backend/python/"
COPY . /home/mcts/

# Build C++ module with current Python 3.12
WORKDIR /home/mcts/backend/core  
RUN rm -f _corridors_mcts.so && scons
# Copy to python modules directory (directory should already exist from COPY operation)
RUN cp _corridors_mcts.so /home/mcts/backend/python/corridors/_corridors_mcts.so

# Build React frontend (after copying project files) - generates fresh package-lock.json
WORKDIR /home/mcts/frontend
RUN npm install
RUN npm run build
# Verify build directory was created
RUN ls -la build/

# Install frontend test dependencies - generates fresh package-lock.json
WORKDIR /home/mcts/tests/frontend
RUN npm install

WORKDIR /home/mcts

# Set Python path for the project
ENV PYTHONPATH="/home/mcts:/home/mcts/backend/python"

# Expose port for unified FastAPI server (serves both API and frontend)
EXPOSE 8000

# Start FastAPI server directly with tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-m", "backend.api.server"]