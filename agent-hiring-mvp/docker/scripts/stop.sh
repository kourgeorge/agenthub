#!/bin/bash

# Docker Compose Management Scripts
# Usage: ./docker/scripts/stop.sh [service]

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

# Function to stop services
stop_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        print_status "Stopping $service service..."
        docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" stop "$service"
    else
        print_status "Stopping all services..."
        docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" down
    fi
    
    print_status "Services stopped successfully!"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [service]"
    echo ""
    echo "Stop Docker services for AgentHub"
    echo ""
    echo "Arguments:"
    echo "  service    Optional. Specific service to stop (e.g., caddy, litellm)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Stop all services"
    echo "  $0 caddy             # Stop only Caddy service"
    echo "  $0 litellm           # Stop only LiteLLM service"
    exit 0
fi

stop_services "$1"
