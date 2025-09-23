# Build Validation Checklist

This document provides a quick validation checklist for ensuring the Python extension builds correctly and can be imported successfully.

## Quick Validation Steps

### 1. Build the Extension
```bash
cd backend/core
scons
```

**Expected output:**
- Should display "Building pybind11 version (no Boost dependencies)"
- Should create `../build/_corridors_mcts.so`
- No compilation errors

### 2. Verify Build Artifacts
```bash
ls -la ../build/_corridors_mcts.so
```

**Expected output:**
- File should exist and be executable
- Size should be > 300KB (contains full MCTS implementation)

### 3. Check Exported Symbols
```bash
nm -D ../build/_corridors_mcts.so | grep PyInit
```

**Expected output:**
- Should show `PyInit__corridors_mcts` symbol
- This is the Python 3 module initialization function

### 4. Test Direct Import
```bash
python -c "import sys; sys.path.insert(0, '../build'); import _corridors_mcts; print('✅ Direct import successful')"
```

**Expected output:**
- No import errors
- Prints success message

### 5. Test Object Creation
```bash
python -c "import sys; sys.path.insert(0, '../build'); import _corridors_mcts; obj = _corridors_mcts._corridors_mcts(1.0, 42, True, False, False, False, True); print('✅ Object creation successful')"
```

**Expected output:**
- No errors during object instantiation
- All constructor parameters accepted

### 6. Test Package Import
```bash
PYTHONPATH='../python:../build' python -c "from corridors import _corridors_mcts; print('✅ Package import successful:', _corridors_mcts.__file__)"
```

**Expected output:**
- Successfully imports through package structure
- Shows path to the built `.so` file

### 7. Test Full Interface
```bash
PYTHONPATH='../python:../build' python -c "
from corridors import _corridors_mcts
obj = _corridors_mcts._corridors_mcts(1.0, 42, True, False, False, False, True)
print('Legal moves:', len(obj.get_legal_moves()))
print('Display:', obj.display()[:50] + '...')
print('Visit count:', obj.get_visit_count())
print('✅ Full interface test successful')
"
```

**Expected output:**
- Shows legal moves count (should be > 0)
- Shows board display (string representation)
- Shows visit count (initially 0)

## CI/CD Integration

Add this validation step to your CI pipeline:

```bash
#!/bin/bash
set -e

echo "=== Building C++ Extension ==="
cd backend/core
scons

echo "=== Validating Build ==="
if [ ! -f "../build/_corridors_mcts.so" ]; then
    echo "❌ Build artifact not found"
    exit 1
fi

echo "=== Testing Import ==="
PYTHONPATH="../python:../build" python -c "
import _corridors_mcts
obj = _corridors_mcts._corridors_mcts(1.0, 42, True, False, False, False, True)
assert len(obj.get_legal_moves()) > 0
assert obj.get_visit_count() == 0
print('✅ All validation tests passed')
"

echo "=== Build Validation Complete ==="
```

## Common Issues and Solutions

### Issue: ImportError "module does not define module export function"
**Cause:** Module name mismatch between source code and filename
**Solution:** Verify `PYBIND11_MODULE(_corridors_mcts, m)` matches filename

### Issue: "No such file or directory" during import
**Cause:** Build artifact not in expected location
**Solution:** Check that SCons outputs to `../build/_corridors_mcts.so`

### Issue: Symbol not found errors
**Cause:** Missing or incorrect Python headers during compilation
**Solution:** Verify `python-config --includes` paths are correct

### Issue: Architecture mismatch
**Cause:** Cross-compilation or mixed architectures
**Solution:** Ensure Python interpreter and compiled extension match (both arm64 or both x86_64)

## Troubleshooting Commands

```bash
# Check Python configuration
python-config --includes
python-config --ldflags

# Check architecture compatibility
file ../build/_corridors_mcts.so
file $(python -c "import sys; print(sys.executable)")

# Inspect build dependencies
ldd ../build/_corridors_mcts.so  # On Linux
otool -L ../build/_corridors_mcts.so  # On macOS

# Debug symbol information
objdump -T ../build/_corridors_mcts.so | grep PyInit  # On Linux
nm -D ../build/_corridors_mcts.so | grep PyInit  # Cross-platform
```

This checklist ensures the build process works correctly and catches issues early in the development cycle.