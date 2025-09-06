#!/usr/bin/env python3
"""Setup script for the Agent Hiring System MVP."""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return success status."""
    try:
        logger.info(f"Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        logger.error("Python 3.9 or higher is required")
        return False
    logger.info(f"Python version: {sys.version}")
    return True


def create_virtual_environment():
    """Create a virtual environment."""
    venv_path = Path("venv")
    if venv_path.exists():
        logger.info("Virtual environment already exists")
        return True
    
    logger.info("Creating virtual environment...")
    return run_command("python -m venv venv")


def install_dependencies():
    """Install Python dependencies."""
    logger.info("Installing dependencies...")
    
    # Determine the pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_cmd = "venv/bin/pip"
    
    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip"):
        return False
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt"):
        return False
    
    logger.info("Dependencies installed successfully")
    return True


def initialize_database():
    """Initialize the database."""
    logger.info("Initializing database...")
    
    # Determine the python command based on OS
    if os.name == 'nt':  # Windows
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_cmd = "venv/bin/python"
    
    return run_command(f"{python_cmd} -m server.database.init_db")


def create_env_file():
    """Create a .env file with default settings."""
    env_file = Path(".env")
    if env_file.exists():
        logger.info(".env file already exists")
        return True
    
    logger.info("Creating .env file...")
    
    env_content = """# Agent Hiring System Environment Variables

# Database Configuration
DB_DATABASE_URL=sqlite:///./agent_hiring.db
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_PRE_PING=true

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Agent Runtime
AGENT_TIMEOUT_SECONDS=300
AGENT_MEMORY_LIMIT_MB=512
AGENT_CPU_LIMIT_PERCENT=50

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        logger.info(".env file created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
        return False


def create_directories():
    """Create necessary directories."""
    directories = [
        "uploads",
        "logs",
        "temp",
        "web-ui/public",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


def setup_web_ui():
    """Setup the web UI (if Node.js is available)."""
    web_ui_path = Path("web-ui")
    if not web_ui_path.exists():
        logger.warning("Web UI directory not found, skipping web UI setup")
        return True
    
    # Check if Node.js is available
    if not run_command("node --version"):
        logger.warning("Node.js not found, skipping web UI setup")
        return True
    
    logger.info("Setting up web UI...")
    
    # Install npm dependencies
    if not run_command("npm install", cwd="web-ui"):
        logger.warning("Failed to install web UI dependencies")
        return False
    
    logger.info("Web UI setup completed")
    return True


def create_startup_scripts():
    """Create startup scripts for different platforms."""
    logger.info("Creating startup scripts...")
    
    # Windows batch file
    windows_script = """@echo off
echo Starting Agent Hiring System...
call venv\\Scripts\\activate
python -m server.main --dev
pause
"""
    
    try:
        with open("start_server.bat", 'w') as f:
            f.write(windows_script)
        logger.info("Created start_server.bat")
    except Exception as e:
        logger.error(f"Failed to create Windows script: {e}")
    
    # Unix/Linux/macOS shell script
    unix_script = """#!/bin/bash
echo "Starting Agent Hiring System..."
source venv/bin/activate
python -m server.main --dev
"""
    
    try:
        with open("start_server.sh", 'w') as f:
            f.write(unix_script)
        # Make executable
        os.chmod("start_server.sh", 0o755)
        logger.info("Created start_server.sh")
    except Exception as e:
        logger.error(f"Failed to create Unix script: {e}")


def main():
    """Main setup function."""
    logger.info("Setting up Agent Hiring System MVP...")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        logger.error("Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        logger.error("Failed to install dependencies")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create .env file
    if not create_env_file():
        logger.error("Failed to create .env file")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database")
        sys.exit(1)
    
    # Setup web UI
    setup_web_ui()
    
    # Create startup scripts
    create_startup_scripts()
    
    logger.info("Setup completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Review and modify the .env file if needed")
    logger.info("2. Start the server:")
    if os.name == 'nt':
        logger.info("   - Windows: run start_server.bat")
    else:
        logger.info("   - Unix/Linux/macOS: ./start_server.sh")
    logger.info("3. Open http://localhost:8000 in your browser")
    logger.info("4. View API documentation at http://localhost:8000/docs")


if __name__ == "__main__":
    main() 