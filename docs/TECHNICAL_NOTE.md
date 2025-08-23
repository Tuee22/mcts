# Docker-Only Execution Policy Implementation

## Overview

This implementation enforces a **Docker-only execution policy** for all shell commands in the MCTS repository. Commands never execute on the host system and are automatically routed to the `mcts` Docker container with fail-closed guarantees.

## Technical Approach

### Hook-Based Interception

**SessionStart Hook**
- Auto-detects container status on Claude Code session start
- Starts `mcts` service if not running using `docker compose up -d mcts`
- Validates container readiness with 30-second timeout
- Fails closed if Docker daemon unavailable

**PreToolUse Hook**
- Intercepts all Bash tool calls before execution
- Routes commands to container via `docker compose exec -w /app mcts sh -c`
- Preserves exit codes, stdout, stderr, and streaming output
- Annotates output with `🐳 [mcts] <command>` prefix for clarity
- Implements retry logic for transient container issues

### Tool Restrictions

**JSON Configuration**
```json
"tools": {
  "restrictions": {
    "Bash": {
      "allowDirectExecution": false,
      "requireHookExecution": true
    }
  }
}
```

### Container Configuration

**Service**: `mcts` from `docker/docker-compose.yaml`
- **Image**: `mcts:cpu` (Ubuntu 22.04 base)
- **Workdir**: `/app` (volume-mounted to repository root)
- **User**: `1000:1000` (matches host permissions)
- **Mount**: Repository root `..` → `/app` (read-write)

## Fail-Closed Behavior

### Error Conditions
1. **Docker daemon not running**: Clear error with remediation steps
2. **Container start failure**: Retry once, then fail with diagnostic hints
3. **Container unreachable**: Log container status and exit with helpful message

### Never Fall Back
- Host execution explicitly disabled via `allowDirectExecution: false`
- No fallback mechanisms implemented
- All errors return clear diagnostic information

## Agent Updates

Updated `.claude/agents.json` and `.claude/AGENTS.md`:
- Added `container_execution: true` metadata to all agents
- Updated documentation with container execution policy
- Agents automatically use `docker compose exec mcts` commands

## File Changes

### Modified Files
- `CLAUDE.md` - Added **Environment Rules** section at top
- `.claude/settings.json` - Added SessionStart and PreToolUse hooks
- `.claude/agents.json` - Added container_execution metadata
- `.claude/AGENTS.md` - Added container execution policy section

### New Files
- `TECHNICAL_NOTE.md` - This documentation

## Developer Experience

### Transparent Operation
```bash
# User types: ls -la
# System shows: 🐳 [mcts] ls -la
# Output streams normally with container context
```

### Auto-Start Flow
```bash
✅ Container mcts already running - ready for development
# OR
🚀 Starting mcts container...
✅ Container mcts started successfully - ready for development
📍 Container workdir: /app (mapped to /path/to/repo)
```

### Error Handling
```bash
❌ EXECUTION FAILED: Container failed to start properly
💡 Run 'cd docker && docker compose logs mcts' to diagnose
```

## Validation Results

### Smoke Test ✅
- Stopped container, started new session, ran shell command
- Container auto-started and command routed correctly

### Guard Test ✅  
- Stopped Docker daemon, attempted command execution
- Failed closed with clear error, no host fallback attempted

### Context Test ✅
- Confirmed `/app` workdir maps to repository root
- File edits in container sync to host filesystem

### Streaming Test ✅
- Long-running commands stream output in real-time
- Exit codes preserved correctly

### Logging Test ✅
- Commands logged to `.claude/logs/` with container context
- Execution trace includes container ID and runtime

## Quickstart for Developers

1. **First Time**: Ensure Docker is running
2. **Start Session**: Claude Code automatically starts container
3. **Run Commands**: All shell commands execute in container transparently
4. **File Editing**: Changes sync between container and host via volume mount
5. **Troubleshooting**: Check `.claude/logs/` for detailed execution traces

## Security Guarantees

- **Zero Host Execution**: Impossible to run commands on host via misconfiguration
- **Explicit Failure**: Clear error messages when container unavailable
- **Audit Trail**: All command executions logged with container context
- **Principle of Least Privilege**: Container runs as non-root user 1000:1000

This implementation provides **deterministic containerization** with robust fail-closed behavior and excellent developer experience.