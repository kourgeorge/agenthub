#!/usr/bin/env python3
"""
Startup script for the AI Agent Hiring System - Phase 1
This script helps you get the system running quickly.
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    print("🤖 AI Agent Hiring System - Phase 1")
    print("=" * 50)
    print()

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import flask
        print("✅ Flask is installed")
    except ImportError:
        print("❌ Flask is not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "httpx"], check=True)
    
    try:
        import httpx
        print("✅ httpx is installed")
    except ImportError:
        print("❌ httpx is not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    
    print()

def check_beeai_server():
    """Check if BeeAI server is running"""
    print("🔍 Checking BeeAI server...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:8333/healthcheck", timeout=5)
        if response.status_code == 200:
            print("✅ BeeAI server is running")
            return True
        else:
            print("❌ BeeAI server is not responding correctly")
            return False
    except Exception:
        print("❌ BeeAI server is not running")
        print("   Please start the BeeAI server first:")
        print("   cd apps/beeai-server && python -m beeai_server")
        return False

def start_flask_demo():
    """Start the Flask demo application"""
    print("🚀 Starting Flask demo application...")
    
    # Change to the demo directory
    demo_dir = Path(__file__).parent
    os.chdir(demo_dir)
    
    # Start the Flask app
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Failed to start Flask demo: {e}")

def open_browser():
    """Open the web browser to the demo"""
    print("🌐 Opening web browser...")
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    try:
        webbrowser.open("http://localhost:5000")
        webbrowser.open("http://localhost:5000/hiring_demo.html")
        print("✅ Browser opened to demo pages")
    except Exception as e:
        print(f"❌ Failed to open browser: {e}")
        print("   Please manually open: http://localhost:5000")

def main():
    print_banner()
    
    # Check dependencies
    check_dependencies()
    
    # Check if BeeAI server is running
    if not check_beeai_server():
        print("⚠️  Please start the BeeAI server first, then run this script again")
        print("   Command: cd apps/beeai-server && python -m beeai_server")
        return
    
    print("🎉 All systems ready!")
    print()
    print("📋 What's available:")
    print("   • Main Demo: http://localhost:5000")
    print("   • Hiring Demo: http://localhost:5000/hiring_demo.html")
    print("   • API Docs: http://localhost:8333/api/v1/docs")
    print("   • Hiring API: http://localhost:8333/api/v1/hiring/agents")
    print()
    
    # Ask user if they want to start the demo
    response = input("🚀 Start the Flask demo? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        # Open browser in background
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start Flask app
        start_flask_demo()
    else:
        print("👋 Demo not started. You can run it manually with:")
        print("   cd apps/beeai-flask-demo && python app.py")

if __name__ == "__main__":
    import os
    main() 