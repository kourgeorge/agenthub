#!/bin/bash

# Docker Compose Management Scripts
# Usage: ./docker/scripts/cleanup.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Function to cleanup Docker resources
cleanup_docker() {
    local force="$1"
    
    print_warning "This will clean up Docker resources for AgentHub"
    print_warning "This includes:"
    echo "  - Stopping all services"
    echo "  - Removing containers"
    echo "  - Removing networks"
    echo "  - Removing volumes (if --force is used)"
    echo ""
    
    if [ "$force" != "true" ]; then
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Cleanup cancelled"
            exit 0
        fi
    fi
    
    print_status "Stopping all services..."
    docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" down
    
    if [ "$force" = "true" ]; then
        print_status "Removing volumes..."
        docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" down -v
    fi
    
    print_status "Cleaning up unused Docker resources..."
    docker system prune -f
    
    print_status "Cleanup completed successfully!"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [--force]"
    echo ""
    echo "Clean up Docker resources for AgentHub"
    echo ""
    echo "Arguments:"
    echo "  --force     Skip confirmation prompt and remove volumes"
    echo ""
    echo "This script will:"
    echo "  - Stop all services"
    echo "  - Remove containers"
    echo "  - Remove networks"
    echo "  - Remove volumes (if --force is used)"
    echo "  - Clean up unused Docker resources"
    exit 0
fi

cleanup_docker "$1"
