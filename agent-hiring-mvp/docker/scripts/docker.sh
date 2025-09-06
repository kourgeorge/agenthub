#!/bin/bash

# Cross-platform Docker management script for AgentHub
# This script detects the platform and uses the appropriate method

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python is not installed or not in PATH"
    echo "Please install Python 3.6 or later"
    exit 1
fi

# Use Python script for cross-platform compatibility
exec "$PYTHON_CMD" "$SCRIPT_DIR/docker.py" "$@"