# CPU-only build (works on both ARM64 and AMD64)
FROM ubuntu:22.04 AS cpu
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

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3.12 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

# CUDA build (AMD64 only)
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04 AS cuda
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

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3.12 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

# Final build stage
FROM ${TARGETARCH} AS final
WORKDIR /home

# Install project dependencies
COPY pyproject.toml poetry.lock* ./
RUN python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); import distutils.util" && \
    find /usr/lib/python3/dist-packages -name "*blinker*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.12/dist-packages -name "*blinker*" -delete 2>/dev/null || true
RUN if [ "${TARGETARCH}" = "cuda" ]; then \
        poetry install --with dev,cuda --no-interaction --no-root; \
    else \
        poetry install --with dev --no-interaction --no-root; \
    fi

# Copy all project files and set up environment
ENV PYTHONPATH="/home/mcts/:/home/mcts/backend/python/"
COPY . /home/mcts/

# Install Poetry dependencies in the project directory
WORKDIR /home/mcts
RUN poetry install --no-interaction --no-root

# Build C++ module with current Python 3.12
WORKDIR /home/mcts/backend/core  
RUN rm -f _corridors_mcts.so && scons
# Copy to python modules directory (directory should already exist from COPY operation)
RUN cp _corridors_mcts.so /home/mcts/backend/python/corridors/_corridors_mcts.so

# Build React frontend (after copying project files)
WORKDIR /home/mcts/frontend
RUN npm ci
RUN npm run build
# Verify build directory was created
RUN ls -la build/

# Install frontend test dependencies
WORKDIR /home/mcts/tests/frontend
RUN npm ci
# Link React dependencies from main frontend to avoid version conflicts
RUN ln -sf /home/mcts/frontend/node_modules/react node_modules/react
RUN ln -sf /home/mcts/frontend/node_modules/react-dom node_modules/react-dom  
RUN ln -sf /home/mcts/frontend/node_modules/@testing-library node_modules/@testing-library
RUN ln -sf /home/mcts/frontend/node_modules/zustand node_modules/zustand
RUN ln -sf /home/mcts/frontend/node_modules/react-hot-toast node_modules/react-hot-toast
RUN ln -sf /home/mcts/frontend/node_modules/socket.io-client node_modules/socket.io-client

# Node.js build tools no longer needed at runtime (frontend is served by FastAPI)

# Tini is installed via apt package above - no additional setup needed

WORKDIR /home/mcts

# Set Python path for the project
ENV PYTHONPATH="/home/mcts:/home/mcts/backend/python"

# Expose port for unified FastAPI server (serves both API and frontend)
EXPOSE 8000

# Start FastAPI server directly with tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-m", "backend.api.server"]