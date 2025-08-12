#!/bin/bash

# Frontend Test Runner for Corridors Game
# This script runs all frontend tests with proper configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
FRONTEND_DIR="$PROJECT_ROOT/frontend"

print_status "Starting Corridors Frontend Test Suite"
print_status "Project root: $PROJECT_ROOT"
print_status "Frontend directory: $FRONTEND_DIR"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    print_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    print_warning "Node modules not found. Installing dependencies..."
    cd "$FRONTEND_DIR"
    npm install
fi

# Run different test categories based on argument
case "${1:-all}" in
    "unit")
        print_status "Running unit tests..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --testPathPattern="(components|services|store)" --coverage
        ;;
    "integration")
        print_status "Running integration tests..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --testPathPattern="integration" --coverage
        ;;
    "e2e")
        print_status "Running E2E tests..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --testPathPattern="e2e" --coverage --timeout=30000
        ;;
    "watch")
        print_status "Running tests in watch mode..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --watch
        ;;
    "coverage")
        print_status "Running all tests with detailed coverage..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --coverage --coverageReporters=text --coverageReporters=lcov --coverageReporters=html
        ;;
    "ci")
        print_status "Running tests in CI mode..."
        cd "$SCRIPT_DIR"
        npx jest --config jest.config.js --ci --coverage --watchAll=false
        ;;
    "all"|*)
        print_status "Running all frontend tests..."
        
        # Run unit tests
        print_status "1/3 Running unit tests..."
        cd "$SCRIPT_DIR"
        if npx jest --config jest.config.js --testPathPattern="(components|services|store)" --coverage --silent; then
            print_success "Unit tests passed"
        else
            print_error "Unit tests failed"
            exit 1
        fi
        
        # Run integration tests
        print_status "2/3 Running integration tests..."
        if npx jest --config jest.config.js --testPathPattern="integration" --coverage --silent; then
            print_success "Integration tests passed"
        else
            print_error "Integration tests failed"
            exit 1
        fi
        
        # Run E2E tests
        print_status "3/3 Running E2E tests..."
        if npx jest --config jest.config.js --testPathPattern="e2e" --coverage --silent --timeout=30000; then
            print_success "E2E tests passed"
        else
            print_error "E2E tests failed"
            exit 1
        fi
        
        print_success "All frontend tests completed successfully!"
        ;;
esac

# Display coverage report location
if [ -f "$SCRIPT_DIR/coverage/lcov-report/index.html" ]; then
    print_status "Coverage report available at: $SCRIPT_DIR/coverage/lcov-report/index.html"
fi

print_success "Test run completed!"