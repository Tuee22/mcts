"""
Playwright configuration for E2E tests.
This configures Playwright to work with pytest-playwright.
"""
import os
from typing import Dict, Union

# Test configuration - Using Union instead of Any for better type safety
config: Dict[
    str,
    Union[
        str,
        int,
        bool,
        Dict[str, Union[str, int, bool, Dict[str, Union[str, int]]]],
        list[Dict[str, Union[str, int, bool, Dict[str, str]]]],
    ],
] = {
    # Test timeout
    "timeout": 30000,
    # Expect timeout
    "expect_timeout": 5000,
    # Fail tests on console errors
    "fail_on_console_error": False,
    # Number of workers for parallel execution
    "workers": 1,  # Serial execution for stability
    # Retry failed tests
    "retries": 1,
    # Reporter configuration
    "reporter": "list",
    # Global test configuration
    "use": {
        # Base URL for navigation
        "base_url": os.environ.get("E2E_FRONTEND_URL", "http://localhost:3002"),
        # Viewport size
        "viewport": {"width": 1280, "height": 720},
        # Ignore HTTPS errors
        "ignore_https_errors": True,
        # Artifacts
        "screenshot": "only-on-failure",
        "video": os.environ.get("E2E_VIDEO", "retain-on-failure"),
        "trace": os.environ.get("E2E_TRACE", "retain-on-failure"),
    },
    # Configure projects for different browsers
    "projects": [
        {
            "name": "chromium",
            "use": {
                "browser_name": "chromium",
                "channel": "chrome",
            },
        },
        {
            "name": "firefox",
            "use": {
                "browser_name": "firefox",
            },
        },
        {
            "name": "webkit",
            "use": {
                "browser_name": "webkit",
            },
        },
    ],
    # Web server configuration - start backend and frontend before tests
    "web_server": [
        {
            "command": "python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8002",
            "port": 8002,
            "timeout": 30 * 1000,
            "reuse_existing_server": not os.environ.get("CI"),
            "env": {
                "MCTS_API_HOST": "0.0.0.0",
                "MCTS_API_PORT": "8002",
                "MCTS_CORS_ORIGINS": "*",
            },
        },
        {
            "command": "cd frontend && npx serve -s build -l 3002",
            "port": 3002,
            "timeout": 30 * 1000,
            "reuse_existing_server": not os.environ.get("CI"),
            "env": {
                "REACT_APP_API_URL": "http://localhost:8002",
                "REACT_APP_WS_URL": "ws://localhost:8002/ws",
            },
        },
    ],
}


# Export for pytest-playwright
def pytest_configure(
    config_obj: object,
) -> Dict[
    str,
    Union[
        str,
        int,
        bool,
        Dict[str, Union[str, int, bool, Dict[str, Union[str, int]]]],
        list[Dict[str, Union[str, int, bool, Dict[str, str]]]],
    ],
]:
    """Configure pytest with Playwright settings."""
    # This is called by pytest-playwright to get configuration
    return config
