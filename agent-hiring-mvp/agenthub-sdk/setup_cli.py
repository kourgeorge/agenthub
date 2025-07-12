#!/usr/bin/env python3
"""
Setup script for AgentHub CLI installation.
"""

import sys
import subprocess
from pathlib import Path


def install_cli():
    """Install the AgentHub CLI tool."""
    print("🚀 Installing AgentHub CLI...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Install in development mode
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                      check=True, cwd=Path(__file__).parent)
        print("✅ AgentHub CLI installed successfully!")
        print("\nUsage:")
        print("  agenthub --help")
        print("  agenthub agent init my-agent")
        print("  agenthub config --author 'Your Name' --email 'your@email.com'")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        print("Try running: pip install -e .")
        sys.exit(1)


if __name__ == "__main__":
    install_cli() 