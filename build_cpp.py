#!/usr/bin/env python3
"""
Simple build script for the C++ extension without Poetry dependencies.
"""
import subprocess
import sys
import os


def main():
    # Change to backend/core directory
    core_dir = os.path.join(os.path.dirname(__file__), "backend", "core")
    os.chdir(core_dir)

    # Python configuration
    python_includes = ["/usr/include/python3.12"]
    pybind11_includes = ["/usr/local/lib/python3.12/dist-packages/pybind11/include"]
    python_libs = ["-lpython3.12"]

    # Source files
    sources = ["_corridors_mcts_pybind.cpp", "corridors_api.cpp", "board.cpp"]

    # Output
    output = "../python/corridors/_corridors_mcts.so"

    # Compiler flags
    flags = ["-shared", "-fPIC", "-O3", "-std=c++17", "-Wno-deprecated-declarations"]

    # Include paths
    includes = []
    for inc in python_includes + pybind11_includes:
        includes.extend(["-I", inc])

    # Build command
    cmd = ["g++"] + flags + includes + sources + ["-o", output] + python_libs

    print(f"Building C++ extension...")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build successful")
        print(f"Output: {output}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
