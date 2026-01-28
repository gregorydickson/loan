#!/bin/bash
# Convenience wrapper for test runner

set -e

# Change to backend directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the Python test runner
python3 run_tests.py "$@"
