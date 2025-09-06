#!/usr/bin/env python3
"""
Cross-platform Docker management script for AgentHub
Works on Windows, Linux, and macOS

Usage: python docker/scripts/docker.py [command] [options]
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(message):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def print_header(message):
    print(f"{Colors.BLUE}[AGENTHUB DOCKER]{Colors.NC} {message}")

def get_project_root():
    """Get the project root directory"""
    script_dir = Path(__file__).parent
    return script_dir.parent.parent

def get_compose_files():
    """Get the docker-compose file paths"""
    project_root = get_project_root()
    compose_dir = project_root / "docker" / "compose"
    return {
        "main": compose_dir / "docker-compose.yml",
        "override": compose_dir / "docker-compose.override.yml"
    }

def run_command(cmd, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return e

def check_docker():
    """Check if Docker is available"""
    result = run_command("docker --version", check=False)
    if result.returncode != 0:
        print_error("Docker is not installed or not in PATH")
        return False
    return True

def check_docker_compose():
    """Check if docker-compose is available"""
    result = run_command("docker-compose --version", check=False)
    if result.returncode != 0:
        print_error("docker-compose is not installed or not in PATH")
        return False
    return True

def get_compose_command():
    """Get the docker-compose command with file paths"""
    compose_files = get_compose_files()
    return f"docker-compose -f {compose_files['main']} -f {compose_files['override']}"

def start_services(service=None):
    """Start Docker services"""
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    if service:
        print_status(f"Starting {service} service...")
        cmd = f"{compose_cmd} up -d {service}"
    else:
        print_status("Starting all services...")
        cmd = f"{compose_cmd} up -d"
    
    result = run_command(cmd)
    if result.returncode == 0:
        print_status("Services started successfully!")
        print_status("Use 'python docker/scripts/docker.py status' to check service status")
        return True
    return False

def stop_services(service=None):
    """Stop Docker services"""
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    if service:
        print_status(f"Stopping {service} service...")
        cmd = f"{compose_cmd} stop {service}"
    else:
        print_status("Stopping all services...")
        cmd = f"{compose_cmd} down"
    
    result = run_command(cmd)
    if result.returncode == 0:
        print_status("Services stopped successfully!")
        return True
    return False

def restart_services(service=None):
    """Restart Docker services"""
    print_status("Restarting services...")
    stop_services(service)
    import time
    time.sleep(2)
    return start_services(service)

def show_status():
    """Show service status"""
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    print_header("Docker Services Status")
    print()
    
    # Show service status
    result = run_command(f"{compose_cmd} ps")
    if result.returncode == 0:
        print(result.stdout)
    
    print()
    print_header("Service URLs")
    print("Caddy (Reverse Proxy): http://localhost:8080")
    print("LiteLLM (if running):  http://localhost:4000")
    print("Prometheus (if running): http://localhost:9091")
    
    print()
    print_header("Useful Commands")
    print("View logs:     python docker/scripts/docker.py logs [service]")
    print("Restart:       python docker/scripts/docker.py restart [service]")
    print("Clean up:      python docker/scripts/docker.py cleanup")
    
    return True

def show_logs(service=None, follow=False):
    """Show service logs"""
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    if follow:
        if service:
            print_status(f"Following logs for {service} service (Ctrl+C to stop)...")
            cmd = f"{compose_cmd} logs -f {service}"
        else:
            print_status("Following logs for all services (Ctrl+C to stop)...")
            cmd = f"{compose_cmd} logs -f"
        
        # For follow mode, we don't capture output
        try:
            subprocess.run(cmd, shell=True)
        except KeyboardInterrupt:
            print("\n[INFO] Log following stopped")
    else:
        if service:
            print_status(f"Showing logs for {service} service...")
            cmd = f"{compose_cmd} logs {service}"
        else:
            print_status("Showing logs for all services...")
            cmd = f"{compose_cmd} logs"
        
        result = run_command(cmd)
        if result.returncode == 0:
            print(result.stdout)
    
    return True

def cleanup(force=False):
    """Clean up Docker resources"""
    print_warning("This will clean up Docker resources for AgentHub")
    print_warning("This includes:")
    print("  - Stopping all services")
    print("  - Removing containers")
    print("  - Removing networks")
    print("  - Removing volumes (if --force is used)")
    print()
    
    if not force:
        try:
            confirm = input("Are you sure you want to continue? (y/N): ")
            if confirm.lower() not in ['y', 'yes']:
                print_status("Cleanup cancelled")
                return True
        except KeyboardInterrupt:
            print("\n[INFO] Cleanup cancelled")
            return True
    
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    print_status("Stopping all services...")
    run_command(f"{compose_cmd} down")
    
    if force:
        print_status("Removing volumes...")
        run_command(f"{compose_cmd} down -v")
    
    print_status("Cleaning up unused Docker resources...")
    run_command("docker system prune -f")
    
    print_status("Cleanup completed successfully!")
    return True

def build_images():
    """Build Docker images"""
    if not check_docker() or not check_docker_compose():
        return False
    
    compose_cmd = get_compose_command()
    
    print_status("Building Docker images...")
    result = run_command(f"{compose_cmd} build")
    if result.returncode == 0:
        print_status("Build completed!")
        return True
    return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="AgentHub Docker Management Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python docker/scripts/docker.py start                    # Start all services
  python docker/scripts/docker.py start caddy             # Start only Caddy
  python docker/scripts/docker.py logs -f litellm         # Follow LiteLLM logs
  python docker/scripts/docker.py status                  # Check service status
  python docker/scripts/docker.py cleanup                 # Clean up resources

Services:
  caddy              Reverse proxy with SSL
  litellm            AI model proxy
  prometheus         Metrics collection
        """
    )
    
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('service', nargs='?', help='Service name (optional)')
    parser.add_argument('-f', '--follow', action='store_true', help='Follow logs in real-time')
    parser.add_argument('--force', action='store_true', help='Force cleanup without confirmation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print_header("AgentHub Docker Management")
    print()
    
    # Change to project root
    project_root = get_project_root()
    os.chdir(project_root)
    
    if args.command == "start":
        success = start_services(args.service)
    elif args.command == "stop":
        success = stop_services(args.service)
    elif args.command == "restart":
        success = restart_services(args.service)
    elif args.command == "status":
        success = show_status()
    elif args.command == "logs":
        success = show_logs(args.service, args.follow)
    elif args.command == "cleanup":
        success = cleanup(args.force)
    elif args.command == "build":
        success = build_images()
    else:
        print_error(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
