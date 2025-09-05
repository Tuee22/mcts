# Backend

This directory contains all backend components of the Corridors MCTS project.

## Structure

- `core/` - C++ MCTS engine and board logic
- `python/corridors/` - Python bindings for the C++ engine  
- `api/` - FastAPI web service

## Building

The C++ core is built using SCons:

```bash
cd backend/core
scons
```

The Python API server can be run with:

```bash
poetry run server
```