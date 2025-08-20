# Claude Code Agents Pipeline

This document describes the automated pipeline setup with four specialized Claude Code agents that enforce code quality through a deterministic post-change chain.

## Pipeline Overview

After every code edit (`Edit`, `Write`, or `MultiEdit`), the system automatically runs:

**Black → MyPy → Build → Tests**

Each stage must complete successfully before proceeding to the next. If any stage fails, the pipeline blocks and directs you to call the appropriate agent to fix the issue.

## The Four Agents

### 1. `@formatter-black`
- **Purpose**: Python code formatting with Black
- **Commands**: `black .` followed by `black --check .`
- **Triggers**: Always runs first in the pipeline
- **Fixes**: Code style and formatting issues

### 2. `@mypy-type-checker`
- **Purpose**: Comprehensive Python type checking and error resolution across entire repository
- **Commands**: `mypy --strict .` (customizable via `MYPY_CMD`)
- **Scope**: ALL Python files including backend/, tests/, tools/, and utilities
- **Approach**: Iterates until exit code 0 in strict mode, prefers precise fixes over `Any`/suppressions
- **Fixes**: Type annotations, import issues, type mismatches, stub file creation/updates

### 3. `@builder-docker`
- **Purpose**: Docker container building and build error resolution
- **Commands**: `docker build -t project-ci .` (customizable via `BUILD_CMD`)
- **Triggers**: When build surface files change or `ALWAYS_BUILD=1`
- **Fixes**: Dockerfile issues, dependency problems, build failures

### 4. `@tester-pytest`
- **Purpose**: Test suite execution and failure resolution
- **Commands**: `pytest -q` (customizable via `TEST_CMD`)
- **Triggers**: When changes occur or `ALWAYS_TEST=1`
- **Fixes**: Test failures, assertions, mock issues, import problems

## Build Surface Detection

The builder agent triggers when these files/paths change:
- **Files**: `Dockerfile`, `.dockerignore`, `compose.yaml`, `docker-compose.yml`
- **Python**: `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements*.txt`, `Pipfile`, `poetry.lock`
- **Build**: `Makefile`
- **Paths**: `docker/`, `scripts/build/`, `.github/workflows/`

## Environment Configuration

Customize the pipeline with these environment variables:

```bash
# Command customization
export MYPY_CMD="mypy --strict"
export TEST_CMD="pytest -v --cov"
export BUILD_CMD="docker build -t my-project ."

# Force stages to always run
export ALWAYS_BUILD=1
export ALWAYS_TEST=1
```

## Unattended Operation

For automated/CI scenarios, use one of these approaches:

### Option 1: Skip All Permissions (Global)
```bash
claude --dangerously-skip-permissions
```

### Option 2: Allow Specific Tools
```bash
claude --allowedTools="black,mypy,docker,pytest,git"
```

## Usage Examples

### Normal Development Flow
1. Edit code files normally
2. Pipeline automatically runs: Black → MyPy → Build → Tests
3. If any stage fails, call the suggested agent:
   ```
   ❌ BLOCKED: MyPy stage failed
   Reason: Type checking failed. There are type errors that need to be resolved.
   
   To fix this issue, please run:
     @mypy-type-checker
   ```

### Manual Agent Invocation
Call agents directly when needed:
```bash
@formatter-black          # Format code with Black
@mypy-type-checker        # Fix type errors
@builder-docker           # Fix build issues
@tester-pytest           # Fix test failures
```

### Pipeline Customization
```bash
# Only run tests, skip build
export ALWAYS_BUILD=0
export ALWAYS_TEST=1

# Use strict mypy settings
export MYPY_CMD="mypy --strict . --disallow-untyped-defs"

# Verbose test output
export TEST_CMD="pytest -v --tb=short"
```

## Pipeline Behavior

- **Idempotent**: Safe to run multiple times
- **Deterministic**: Always runs stages in the same order
- **Blocking**: Stops at first failure with clear guidance
- **Smart**: Skips build/test stages when not needed
- **Configurable**: Environment variables control behavior

## Files Created

```
.claude/
├── agents/
│   ├── formatter-black.md      # Black formatting agent
│   ├── mypy-type-checker.md    # MyPy type checking agent  
│   ├── builder-docker.md       # Docker build agent
│   └── tester-pytest.md        # PyTest testing agent
├── hooks/
│   └── on-change-chain.py      # Post-change hook script
└── settings.json               # Hook configuration
```

## Troubleshooting

### Hook Not Running
- Verify `.claude/settings.json` exists and is valid JSON
- Check that `.claude/hooks/on-change-chain.py` is executable
- Ensure Python 3 is available in PATH

### Agent Not Found
- Verify agent files exist in `.claude/agents/`
- Check agent filenames match exactly (case-sensitive)
- Ensure agents are in the correct markdown format

### Pipeline Failures
- Read the specific error message and reason
- Call the suggested agent to fix the issue
- Agents will iterate until the problem is resolved

### Customization Issues
- Check environment variable syntax and values
- Verify custom commands are available in PATH
- Test commands manually before using in pipeline