#!/bin/bash

# Docker Compose Management Scripts
# Usage: ./docker/scripts/start.sh [service]

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

# Function to start services
start_services() {
    local service="$1"
    
    if [ -n "$service" ]; then
        print_status "Starting $service service..."
        docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" up -d "$service"
    else
        print_status "Starting all services..."
        docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" up -d
    fi
    
    print_status "Services started successfully!"
    print_status "Use './docker/scripts/status.sh' to check service status"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [service]"
    echo ""
    echo "Start Docker services for AgentHub"
    echo ""
    echo "Arguments:"
    echo "  service    Optional. Specific service to start (e.g., caddy, litellm)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start all services"
    echo "  $0 caddy             # Start only Caddy service"
    echo "  $0 litellm           # Start only LiteLLM service"
    exit 0
fi

start_services "$1"
