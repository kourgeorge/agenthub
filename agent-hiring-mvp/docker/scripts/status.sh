#!/bin/bash

# Docker Compose Management Scripts
# Usage: ./docker/scripts/status.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")/compose"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to project root
cd "$PROJECT_ROOT"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

# Function to check service status
check_status() {
    print_header "Docker Services Status"
    echo ""
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    # Show service status
    docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" ps
    
    echo ""
    print_header "Service URLs"
    echo "Caddy (Reverse Proxy): http://localhost:8080"
    echo "LiteLLM (if running):  http://localhost:4000"
    echo "Prometheus (if running): http://localhost:9091"
    
    echo ""
    print_header "Useful Commands"
    echo "View logs:     ./docker/scripts/logs.sh [service]"
    echo "Restart:       ./docker/scripts/restart.sh [service]"
    echo "Clean up:      ./docker/scripts/cleanup.sh"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0"
    echo ""
    echo "Check the status of Docker services for AgentHub"
    echo ""
    echo "This script will show:"
    echo "  - Service status (running/stopped)"
    echo "  - Service URLs"
    echo "  - Useful commands"
    exit 0
fi

check_status
