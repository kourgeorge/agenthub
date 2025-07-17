#!/usr/bin/env python3
"""
Dependency installation script for ACL Review Agent
Helps resolve compatibility issues with Python 3.13+
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🔧 ACL Review Agent - Dependency Installation")
    print("=" * 50)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version >= (3, 13):
        print("⚠️  Detected Python 3.13+ - using compatibility fixes")
    
    # Upgrade pip first
    print("\n📦 Upgrading pip...")
    run_command(f"{sys.executable} -m pip install --upgrade pip")
    
    # Install core dependencies with specific versions for Python 3.13+ compatibility
    print("\n📦 Installing core dependencies...")
    
    # Install urllib3 first (required for requests)
    if not run_command(f"{sys.executable} -m pip install 'urllib3>=2.0.0'"):
        print("Failed to install urllib3")
        return False
    
    # Install requests with compatible version
    if not run_command(f"{sys.executable} -m pip install 'requests>=2.31.0'"):
        print("Failed to install requests")
        return False
    
    # Install other dependencies
    dependencies = [
        "openai",
        "python-dotenv",
        "beautifulsoup4",
        "PyPDF2",
        "arxiv",
        "scholarly",
        "pymupdf",
        "nltk",
        "scikit-learn",
        "openreview-py",
        "semanticscholar"
    ]
    
    for dep in dependencies:
        if not run_command(f"{sys.executable} -m pip install {dep}"):
            print(f"Failed to install {dep}")
            return False
    
    # Download NLTK data
    print("\n📚 Downloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✅ NLTK data downloaded")
    except Exception as e:
        print(f"⚠️  NLTK data download failed: {e}")
    
    print("\n🎉 Installation completed successfully!")
    print("\nTo test the agent, run:")
    print("python test_acl_review.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 