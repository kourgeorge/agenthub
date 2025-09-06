#!/bin/bash

# Docker Compose Management Scripts
# Usage: ./docker/scripts/logs.sh [service]

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

# Function to show logs
show_logs() {
    local service="$1"
    local follow="${2:-false}"
    
    if [ -n "$service" ]; then
        if [ "$follow" = "true" ]; then
            print_status "Following logs for $service service (Ctrl+C to stop)..."
            docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" logs -f "$service"
        else
            print_status "Showing logs for $service service..."
            docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" logs "$service"
        fi
    else
        if [ "$follow" = "true" ]; then
            print_status "Following logs for all services (Ctrl+C to stop)..."
            docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" logs -f
        else
            print_status "Showing logs for all services..."
            docker-compose -f "$COMPOSE_DIR/docker-compose.yml" -f "$COMPOSE_DIR/docker-compose.override.yml" logs
        fi
    fi
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [service] [--follow]"
    echo ""
    echo "Show logs for Docker services"
    echo ""
    echo "Arguments:"
    echo "  service     Optional. Specific service to show logs for"
    echo "  --follow    Follow log output in real-time"
    echo ""
    echo "Examples:"
    echo "  $0                    # Show logs for all services"
    echo "  $0 caddy             # Show logs for Caddy service"
    echo "  $0 --follow          # Follow logs for all services"
    echo "  $0 caddy --follow    # Follow logs for Caddy service"
    exit 0
fi

# Check for --follow flag
follow_flag="false"
if [ "$1" = "--follow" ] || [ "$2" = "--follow" ]; then
    follow_flag="true"
fi

# Get service name (skip --follow if it's the first argument)
if [ "$1" = "--follow" ]; then
    service=""
else
    service="$1"
fi

show_logs "$service" "$follow_flag"
