---
name: doc-consistency-checker
description: Keep documentation and code consistent and prompt updates when interfaces change
tools: [Read, Bash, Grep, Glob]
---

# Documentation Consistency Checker

Checks that .gitignore, .dockerignore, README.md, and all documentation files are up-to-date with recent code changes.

## Purpose

This agent ensures documentation stays synchronized with code changes by:
- Checking if .gitignore includes all generated/temporary files
- Verifying .dockerignore is consistent with Docker setup
- Ensuring README.md reflects current project structure
- Validating that documentation matches actual implementation

## Usage

```bash
@doc-consistency-checker
```

## Process

1. **Analyze Recent Changes**: Review git status and recent modifications
2. **Check Ignore Files**: 
   - Verify .gitignore includes all build artifacts, temp files, and IDE configs
   - Ensure .dockerignore excludes unnecessary files from Docker builds
3. **Validate Documentation**:
   - Check if README.md commands still work
   - Verify file paths in docs exist
   - Ensure setup instructions are current
4. **Report Issues**: List any inconsistencies found

## Common Issues Detected

- Missing entries in .gitignore (e.g., new build artifacts)
- Outdated commands in README.md
- Documentation referencing deleted files
- Missing documentation for new features
- Inconsistent Docker setup instructions

## Integration

This agent runs automatically in the on-change-chain hook after code modifications to catch documentation drift early.