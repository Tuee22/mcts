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
    python3-dev python3-distutils python3-setuptools

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
    python3-dev python3-distutils python3-setuptools

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
COPY pyproject.toml ./
RUN python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); import distutils.util" && \
    find /usr/lib/python3/dist-packages -name "*blinker*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.12/dist-packages -name "*blinker*" -delete 2>/dev/null || true
RUN if [ "${TARGETARCH}" = "cuda" ]; then \
        poetry install --with dev,cuda --no-interaction --no-root; \
    else \
        poetry install --with dev --no-interaction --no-root; \
    fi

# Copy all project files and set up environment
ENV PYTHONPATH="/home/python/:/home/mcts/python/"
COPY . /home/mcts/

# Build C++ module with current Python 3.12
WORKDIR /home/mcts/src  
RUN rm -f _corridors_mcts.so && scons
# Copy to python modules directory  
RUN mkdir -p /home/mcts/python/corridors && cp _corridors_mcts.so /home/mcts/python/corridors/_corridors_mcts.so
WORKDIR /home

EXPOSE 8888 8786 8787
CMD jupyter lab --ip=0.0.0.0 --port=8888 --LabApp.token="" --notebook-dir='/home' --no-browser --allow-root