# Claude Code Agent Registry

This document provides an overview of all available Claude Code agents for the MCTS project, their purposes, and when to use them.

## **CONTAINER EXECUTION POLICY**

**ALL AGENTS EXECUTE COMMANDS INSIDE THE DOCKER CONTAINER**
- Container: `mcts` service from `docker/docker-compose.yaml`
- Workdir: `/app` (mapped to repository root)
- Auto-start: Container started automatically if not running
- Fail-closed: Never execute commands on host system

## Core Quality Assurance Agents

### @formatter-black
**Purpose**: Python code formatting with Black  
**Command**: `black .`  
**When to use**: 
- Code formatting issues detected by the post-change hook
- Before committing new Python code
- When collaborating to ensure consistent formatting

**What it does**:
- Runs Black formatter on all Python files
- Verifies formatting compliance with `black --check`
- Follows PEP 8 style guidelines
- Ensures consistent code style across the project

---

### @mypy-type-checker
**Purpose**: Comprehensive static type checking with zero tolerance policy  
**Command**: `mypy --strict .`  
**When to use**:
- Type errors detected by the post-change hook
- After adding new Python code or dependencies
- When encountering Any, cast(), or type: ignore usage

**What it does**:
- Runs MyPy in strict mode on entire repository
- **Zero tolerance**: Iterates indefinitely until ZERO errors remain
- Never accepts Any, cast(), or type: ignore
- Creates custom type stubs for external dependencies
- Prioritizes core code (`backend/`) then tests (`tests/`) then utilities

**Policies**:
- No Any types allowed anywhere
- No cast() usage
- No type: ignore comments
- Custom stubs replace any third-party stubs using Any
- Will not stop until `mypy --strict .` exits with code 0

---

### @builder-docker
**Purpose**: Docker container builds for development and CI  
**Command**: `docker build -t mcts-ci .`  
**When to use**:
- Build errors detected by the post-change hook
- After changes to Dockerfile, requirements, or C++ code
- Before deployment or CI validation

**What it does**:
- Builds Docker containers for CPU and GPU variants
- Validates all dependencies and compilation
- Ensures consistent build environment
- Tests container functionality

---

### @tester-pytest
**Purpose**: Test suite execution and validation  
**Command**: `pytest -q`  
**When to use**:
- Test failures detected by the post-change hook
- After implementing new features or bug fixes
- Before merging code changes

**What it does**:
- Runs comprehensive test suite with pytest
- Includes integration tests, performance tests, and edge cases
- Validates Python/C++ bindings
- Ensures all functionality remains working

---

### @no-git-commits
**Purpose**: Ensures agents never make git commits  
**When to use**: Always active - this is a policy agent

**What it does**:
- Prevents any agent from making git commits automatically
- User retains full control over version control
- Agents focus on code quality, not git operations

## Specialized Build Agents

### @builder-cpu
**Purpose**: CPU-only Docker builds  
**Command**: `docker build -f docker/Dockerfile.cpu -t mcts-cpu .`  
**When to use**: 
- Building for CPU-only environments
- Testing without GPU dependencies
- CI/CD pipelines without GPU support

---

### @builder-gpu  
**Purpose**: GPU-enabled Docker builds (AMD64 only)  
**Command**: `docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build`  
**When to use**:
- Building for GPU-accelerated environments
- Testing CUDA/OpenCL functionality
- Performance-critical deployments

## Agent Usage Patterns

### Post-Change Hook Integration
The post-change hook (`.claude/hooks/on-change-chain.py`) automatically recommends agents when stages fail:

```bash
❌ Format FAILED (exit code: 1)
📋 Run agent: @formatter-black
🔄 Or fix issues manually and retry
```

### Manual Agent Execution
Run agents directly for proactive quality assurance:

```bash
# Format all code
@formatter-black

# Comprehensive type checking  
@mypy-type-checker

# Build validation
@builder-docker

# Test everything
@tester-pytest
```

### Sequential Quality Pipeline
For comprehensive quality assurance, run agents in this order:

1. `@formatter-black` - Ensure consistent formatting
2. `@mypy-type-checker` - Achieve zero type errors  
3. `@builder-docker` - Validate build integrity
4. `@tester-pytest` - Confirm all functionality

## Environment Configuration

### Post-Change Hook Variables
Control the automatic pipeline with environment variables:

```bash
export MCTS_FORMAT_CMD="black ."
export MCTS_TYPECHECK_CMD="mypy --strict ."
export MCTS_BUILD_CMD="docker build -t mcts-ci ."
export MCTS_TEST_CMD="pytest -q"
export MCTS_SKIP_BUILD="false"
export MCTS_SKIP_TESTS="false"
export MCTS_VERBOSE="true"
export MCTS_FAIL_FAST="true"
```

### Agent-Specific Settings
Some agents respect additional environment variables:

- **MyPy**: `MYPY_CONFIG_FILE` for custom configuration
- **Docker**: `DOCKER_BUILDKIT=1` for enhanced builds
- **Pytest**: `PYTEST_ARGS` for additional test options

## Best Practices

### Development Workflow
1. **Before coding**: Run `@formatter-black` and `@mypy-type-checker`
2. **During development**: Let post-change hook catch issues automatically
3. **Before committing**: Run full pipeline manually to ensure quality
4. **Before deployment**: Use `@builder-docker` to validate containers

### Troubleshooting
- **Tool not found**: Install missing dependencies or use Poetry environment
- **Agent stuck**: Use `MCTS_VERBOSE=true` for detailed output
- **Build failures**: Check Docker daemon and available resources
- **Type errors**: Let `@mypy-type-checker` iterate until resolution

### Contributing
When adding new agents:
1. Create agent file in `.claude/agents/`
2. Add entry to this registry
3. Update machine-readable registry file
4. Test integration with post-change hook
5. Document any new environment variables

## Agent Files Location
All agent definitions are stored in `.claude/agents/`:
- `formatter-black.md`
- `mypy-type-checker.md` 
- `builder-docker.md`
- `tester-pytest.md`
- `no-git-commits.md`
- `builder-cpu.md` (if applicable)
- `builder-gpu.md` (if applicable)

## Hook Configuration
Post-change hook configuration in `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": {
      "command": "python3 .claude/hooks/on-change-chain.py",
      "triggers": ["Edit", "Write", "MultiEdit"],
      "description": "Automatically runs Format → Type Check → Build → Tests pipeline"
    }
  }
}
```