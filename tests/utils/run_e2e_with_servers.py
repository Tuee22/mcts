#!/usr/bin/env python
"""Run E2E tests with proper server setup."""

import os
import subprocess
import sys
import time
from typing import Optional

import requests


def check_server(url: str, name: str) -> bool:
    """Check if a server is running."""
    try:
        response = requests.get(url, timeout=2)
        if response.status_code in [200, 304]:
            print(f"✅ {name} server already running at {url}")
            return True
    except Exception:
        pass
    return False


def start_backend(port: str = "8002") -> subprocess.Popen[bytes]:
    """Start the backend server."""
    env = os.environ.copy()
    env.update(
        {
            "MCTS_API_HOST": "0.0.0.0",
            "MCTS_API_PORT": port,
            "MCTS_CORS_ORIGINS": "*",  # Allow all origins for E2E tests
        }
    )

    print(f"🚀 Starting backend server on port {port}...")
    process: subprocess.Popen[bytes] = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.api.server:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for backend to be ready
    for i in range(30):
        if check_server(f"http://localhost:{port}/health", "Backend"):
            return process
        time.sleep(1)

    # Failed to start
    stdout, stderr = process.communicate(timeout=5)
    print(f"❌ Backend stdout: {stdout.decode() if stdout else 'None'}")
    print(f"❌ Backend stderr: {stderr.decode() if stderr else 'None'}")
    process.terminate()
    raise RuntimeError("Backend server failed to start")


def start_frontend(
    port: str = "3002", backend_port: str = "8002"
) -> subprocess.Popen[bytes]:
    """Start the frontend server."""
    env = os.environ.copy()
    env.update(
        {
            "REACT_APP_API_URL": f"http://localhost:{backend_port}",
            "REACT_APP_WS_URL": f"ws://localhost:{backend_port}/ws",
            "PORT": port,
        }
    )

    print(f"🚀 Starting frontend server on port {port}...")
    process: subprocess.Popen[bytes] = subprocess.Popen(
        ["npx", "serve", "-s", "build", "-l", port],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for frontend to be ready
    for i in range(30):
        if check_server(f"http://localhost:{port}", "Frontend"):
            return process
        time.sleep(1)

    # Failed to start
    stdout, stderr = process.communicate(timeout=5)
    print(f"❌ Frontend stdout: {stdout.decode() if stdout else 'None'}")
    print(f"❌ Frontend stderr: {stderr.decode() if stderr else 'None'}")
    process.terminate()
    raise RuntimeError("Frontend server failed to start")


def main() -> int:
    """Run E2E tests with proper server setup."""
    backend_process: Optional[subprocess.Popen[bytes]] = None
    frontend_process: Optional[subprocess.Popen[bytes]] = None

    try:
        # Start servers if not already running
        if not check_server("http://localhost:8002/health", "Backend"):
            backend_process = start_backend()

        if not check_server("http://localhost:3002", "Frontend"):
            frontend_process = start_frontend()

        # Set environment variables for E2E tests
        os.environ.update(
            {
                "E2E_BACKEND_URL": "http://localhost:8002",
                "E2E_FRONTEND_URL": "http://localhost:3002",
                "E2E_WS_URL": "ws://localhost:8002/ws",
                "E2E_HEADLESS": "true",
            }
        )

        # Run E2E tests
        print("\n🧪 Running E2E tests...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/e2e/", "-v"],
            cwd=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
        )

        return result.returncode

    finally:
        # Cleanup servers
        if backend_process:
            print("\n🛑 Stopping backend server...")
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
                backend_process.wait()

        if frontend_process:
            print("🛑 Stopping frontend server...")
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
                frontend_process.wait()


if __name__ == "__main__":
    sys.exit(main())
