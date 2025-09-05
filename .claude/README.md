# Claude Code Agent System

Comprehensive automated quality assurance system for the MCTS repository using Claude Code agents and hooks.

## ⚠️ Critical Environmental Issue

**Hook System Not Functional**: In this Claude Code environment, the settings.json hook configuration is not being executed. This means:

- ❌ PreToolUse hooks don't trigger before Bash commands
- ❌ PostToolUse hooks don't trigger after file modifications  
- ❌ Automated quality pipeline requires manual invocation
- ❌ Git commit blocking relies on behavioral discipline, not technical enforcement

**Workarounds Available**:
- Git commits are blocked by the git-commit-guard.py hook
- Rely on agent behavioral policies for git commit prevention
- Manually run quality checks: `python3 .claude/hooks/quality-gate-safe.py`

## Overview

This system automatically runs quality checks after every code change, ensuring consistent formatting, type safety, test coverage, and code quality. It prevents issues from entering the codebase while maintaining high development velocity.

## Architecture

### Automated Quality Pipeline

Every file modification (Edit, Write, MultiEdit) triggers a comprehensive quality pipeline:

```
File Change → Format → Type Check → Test Generation → Tests → Coverage → Review
```

**Execution Flow:**
1. **Format Stage** - Black formatting (auto-fix)
2. **Type Check Stage** - MyPy strict mode (must pass)  
3. **Test Generation Stage** - Create/update tests for new code
4. **Test Stage** - Run full test suite (must pass)
5. **Coverage Stage** - Verify coverage meets threshold (90%)
6. **Review Stage** - Automated security and quality review

### Batching and Performance

The system includes intelligent batching to prevent excessive runs:
- **Batching Window**: 30 seconds after last change
- **Single Execution**: Multiple rapid edits trigger pipeline only once
- **Docker Integration**: All commands run inside containers for consistency

## Agent Roles and Permissions

### Implementation Agents (Read/Write)
- **`@formatter-black`** - Python code formatting with Black
- **`@mypy-type-checker`** - Type checking and error resolution  
- **`@test-writer`** - Generate and update unit tests
- **`@builder-docker`** - Docker container builds
- **`@tester-pytest`** - Test execution and debugging

### Analysis Agents (Read-Only)
- **`@code-reviewer`** - Security, style, and maintainability review
- **`@doc-consistency-checker`** - Documentation consistency analysis

### Policy Agents
- **`@no-git-commits`** - Prevents automatic git commits

## Usage Guide

### Automatic Operation

The system runs automatically - no manual intervention required:

1. **Make Code Changes**: Edit, Write, or MultiEdit files
2. **Pipeline Triggers**: Quality checks run automatically  
3. **View Results**: Pipeline output shows pass/fail status
4. **Fix Issues**: Use recommended agents for failures

### Manual Agent Invocation

Call agents directly when needed:

```bash
# Format code manually
@formatter-black

# Fix type errors
@mypy-type-checker

# Generate tests for new code  
@test-writer

# Get code review
@code-reviewer

# Check documentation consistency
@doc-consistency-checker
```

### Quality Gates and Exit Codes

| Exit Code | Stage | Meaning |
|-----------|-------|---------|
| 0 | All | Success - all checks passed |
| 1 | Format | Code formatting required |
| 2 | Type Check | Type errors found |
| 3 | Test Generation | Test creation failed |
| 4 | Tests | Test failures |
| 5 | Coverage | Below threshold (90%) |
| 6 | Review | Critical issues found |
| 7 | Setup | Tool/environment error |

## Quick Start

1. **Make a Code Change**: Edit any Python file
2. **Watch Pipeline Run**: Automatic quality checks execute (if hooks work)
3. **Fix Any Issues**: Use suggested agents (@formatter-black, @mypy-type-checker, etc.)
4. **Pipeline Passes**: Code is ready for commit

**Manual Quality Check** (since hooks don't work):
```bash
python3 .claude/hooks/quality-gate-safe.py
```

**Git Commit Protection**:
```bash
git commit -m "message"                    # Blocked by git-commit-guard.py hook
MCTS_ALLOW_COMMIT=1 git commit -m "message"    # Allowed when authorized
```

## Troubleshooting

### Common Issues

**Pipeline Not Running**: Hooks are non-functional - run manually
**Format Failures**: Run `@formatter-black`  
**Type Errors**: Run `@mypy-type-checker`
**Test Failures**: Run `@tester-pytest`
**Git Commits Blocked**: Enforced by git-commit-guard.py PreToolUse hook

## Configuration

### Environment Variables

Control pipeline behavior:

```bash
# Pipeline Control
export MCTS_FAIL_FAST="true"          # Stop on first failure
export MCTS_VERBOSE="false"           # Detailed output
export COVERAGE_THRESHOLD="90"        # Minimum coverage %

# Review Settings  
export REVIEW_SEVERITY="MAJOR"        # CRITICAL/MAJOR/MINOR
export REVIEW_FOCUS="SECURITY"        # SECURITY/PERFORMANCE/STYLE
```

### Quality Standards

**Formatting**: Black with PEP 8 compliance (auto-fix)
**Type Checking**: MyPy strict mode (zero tolerance)
**Testing**: 90% minimum coverage with comprehensive test suite
**Security**: Static analysis for vulnerabilities and secrets

### Security Features

- **Least Privilege**: Agents have minimum required permissions
- **Container Isolation**: All commands run in Docker
- **Command Filtering**: Bash commands are restricted and logged
- **No Auto-commits**: Git commits require explicit user approval

This system ensures high code quality while maintaining developer productivity through intelligent automation and clear feedback loops.