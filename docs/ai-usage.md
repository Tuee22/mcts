# Claude Code Workflow Usage Guide

This guide covers the Claude Code workflow protection system that prevents "no low surrogate" errors and ensures reliable AI-assisted development.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding the Problem](#understanding-the-problem)
3. [Defense Layers](#defense-layers)
4. [Daily Workflow](#daily-workflow)
5. [Troubleshooting](#troubleshooting)
6. [Configuration](#configuration)
7. [Advanced Usage](#advanced-usage)

## Quick Start

### Starting a New AI Session

```bash
# Start a fresh, clean Claude Code session
npm run ai:session:new

# Verify your setup is working
npm run ai:verify
```

### Basic Commands

```bash
# Check for encoding issues (run before big changes)
npm run sanitize:check

# Fix any encoding issues found
npm run sanitize:fix

# Check payload size before large requests
npm run ai:plan
```

## Understanding the Problem

### What is "no low surrogate" error?

This error occurs when:
1. **Unpaired UTF-16 surrogates** exist in your code or output
2. **Large payloads** overwhelm Claude's transport layer
3. **Binary data** gets included in text requests

### Common Causes

- Copy-pasting from external sources with encoding issues
- Generated files with binary content
- Large bash outputs captured in Claude sessions
- Files with mixed encoding formats

## Defense Layers

Our system provides **defense-in-depth** protection:

### 1. 🛡️ Editor-Level Prevention
- **.editorconfig**: Forces UTF-8 encoding in all editors
- **VS Code settings**: Disables encoding auto-detection
- **File associations**: Ensures consistent text file handling

### 2. 🔍 Repository Scanning
- **Pre-commit hooks**: Block commits with surrogate issues
- **CI validation**: Prevent merging problematic code
- **Manual scanning**: Check repository health anytime

### 3. 📏 Payload Management
- **Size limits**: Prevent oversized requests (200KB default)
- **Auto-chunking**: Break large tasks into manageable pieces
- **Deny lists**: Exclude problematic directories automatically

### 4. 🧹 Active Sanitization
- **String utilities**: Clean text before processing
- **File sanitization**: Fix encoding issues automatically
- **Safe truncation**: Preserve surrogate pairs when shortening text

## Daily Workflow

### Starting Your Day

```bash
# 1. Check repository health
npm run sanitize:check

# 2. If issues found, fix them
npm run sanitize:fix

# 3. Start fresh AI session
npm run ai:session:new
```

### During Development

```bash
# Before committing (automatic via pre-commit hook)
git add .
git commit -m "Your changes"  # Hook will check for issues

# Before large AI requests
npm run ai:plan  # Checks payload size
```

### When Things Go Wrong

```bash
# If you get surrogate errors:
npm run sanitize:fix

# If payloads are too large:
npm run ai:plan --chunk  # Get chunking strategy

# If AI session gets "tainted":
npm run ai:session:new  # Start fresh
```

## Troubleshooting

### Error: "no low surrogate found"

**Cause**: Unpaired UTF-16 surrogate characters in your code

**Solution**:
```bash
# Find and fix the issues
npm run sanitize:check  # Shows locations
npm run sanitize:fix    # Fixes automatically

# Check specific file
node tools/sanitize.js --check path/to/file.js
python tools/string_utils.py check path/to/file.py
```

### Error: Request too large

**Cause**: Payload exceeds size limits

**Solution**:
```bash
# Check what's causing the size
npm run ai:plan

# Get chunking recommendations
npm run ai:plan --chunk

# Exclude large directories in .claude/settings.local.json
```

### Error: Binary data in request

**Cause**: Binary files included in Claude request

**Solution**:
- Check `.claude/settings.local.json` deny list
- Add patterns to `.sanitizeignore`
- Use `npm run ai:session:new` to reset

### Pre-commit Hook Blocking Commits

**Cause**: Surrogate characters in staged files

**Solution**:
```bash
# See what's wrong
git status

# Fix the issues
npm run sanitize:fix

# Stage and commit again
git add .
git commit -m "Your message"
```

### CI Build Failing on Encoding Check

**Cause**: Repository has encoding issues

**Solution**:
```bash
# Fix locally and push
npm run sanitize:fix
git add .
git commit -m "fix: resolve encoding issues"
git push
```

## Configuration

### Claude Settings (`.claude/settings.local.json`)

```json
{
  "permissions": {
    "deny": [
      "Read(**/*node_modules/**)",
      "Read(**/build/**)",
      "Read(**/dist/**)",
      "Read(**/*.snap)",
      "Read(**/*.log)"
    ]
  }
}
```

### Payload Limits (`tools/payload-guard.js`)

```bash
# Set custom limits (in bytes)
node tools/payload-guard.js --set-limit 300000

# Check current configuration
node tools/payload-guard.js --config
```

### Sanitizer Ignore Patterns (`.sanitizeignore`)

```
# Binary files to never scan
*.png
*.jpg
*.pdf

# Large directories
node_modules/
build/
```

### Git Hook Setup

```bash
# Install the pre-commit hook
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Advanced Usage

### Custom String Sanitization

**Node.js:**
```javascript
const { stripUnpairedSurrogates, isUtf8Safe } = require('./tools/string-utils');

// Check if string is safe
if (!isUtf8Safe(myString)) {
  // Sanitize it
  myString = stripUnpairedSurrogates(myString);
}
```

**Python:**
```python
from tools.string_utils import strip_unpaired_surrogates, is_utf8_safe

# Check if string is safe
if not is_utf8_safe(my_string):
    # Sanitize it
    my_string = strip_unpaired_surrogates(my_string)
```

### Custom Chunking Strategies

Create `.claude/payload-config.json`:

```json
{
  "maxPayloadSize": 300000,
  "chunkPatterns": {
    "components": ["src/components/**/*.{js,tsx}"],
    "utils": ["src/utils/**/*.js"],
    "tests": ["tests/**/*.test.js"]
  }
}
```

### Batch Processing Files

```bash
# Scan specific directory
find src/ -name "*.js" | xargs -I {} node tools/sanitize.js --check {}

# Fix all Python files
find . -name "*.py" -exec python tools/string_utils.py fix {} \;
```

### Integration with Build Systems

**In package.json scripts:**
```json
{
  "scripts": {
    "prebuild": "npm run sanitize:check",
    "pretest": "npm run sanitize:check",
    "lint": "npm run sanitize:check && eslint ."
  }
}
```

### Docker Integration

The tools work inside Docker containers:

```bash
# In Docker container
docker compose exec mcts npm run sanitize:check
docker compose exec mcts npm run ai:plan
```

## Best Practices

### 1. Session Hygiene
- Start fresh sessions for new features
- Don't reuse sessions with large outputs
- Use chunking for complex refactors

### 2. File Management
- Keep binary files out of src directories
- Use appropriate `.gitignore` patterns
- Regular cleanup of generated files

### 3. Team Coordination
- Run verification before sharing: `npm run ai:verify`
- Document chunking strategies in README
- Share Claude settings via `.claude/settings.local.json`

### 4. Monitoring
- Set up CI checks for all PRs
- Regular repository health checks
- Monitor payload sizes during development

## FAQ

**Q: Do I need to run these tools manually every time?**
A: No. Pre-commit hooks catch most issues automatically. Manual runs are for troubleshooting.

**Q: Will these tools slow down my development?**
A: The checks are fast (<1 second). The protection prevents much slower debugging sessions.

**Q: Can I disable the protection temporarily?**
A: Yes, but not recommended. You can override with `--no-verify` on commits.

**Q: What if ripgrep is not installed?**
A: The tools automatically fall back to Node.js scanning. Ripgrep is faster but optional.

**Q: How do I handle team members without Node.js?**
A: Python alternatives are provided. CI checks catch issues regardless.

---

## Quick Reference

```bash
# Health checks
npm run sanitize:check        # Check encoding issues
npm run ai:plan              # Check payload size  
npm run ai:verify            # Verify full setup

# Fixes
npm run sanitize:fix         # Fix encoding issues
npm run ai:plan --chunk      # Get chunking strategy

# Session management  
npm run ai:session:new       # Start clean session

# Manual tools
node tools/sanitize.js --help
python tools/string_utils.py --help
node tools/payload-guard.js --help
```

For more help, see: [CLAUDE.md](../CLAUDE.md) | [Repository README](../README.md)