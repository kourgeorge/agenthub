#!/usr/bin/env python3
"""
Example script demonstrating the AgentHub CLI usage.
This script shows how to create, validate, test, and publish an agent.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result

def main():
    """Demonstrate CLI usage."""
    print("🚀 AgentHub CLI Demo")
    print("=" * 50)
    
    # Check if CLI is installed
    result = run_command("agenthub --version")
    if result.returncode != 0:
        print("❌ AgentHub CLI not found. Please install it first:")
        print("   cd agent-hiring-mvp/agenthub-sdk")
        print("   python setup_cli.py")
        sys.exit(1)
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n📁 Working in: {temp_dir}")
        
        # Step 1: Configure CLI
        print("\n1️⃣ Configuring CLI...")
        run_command("agenthub config --author 'Demo User' --email 'demo@example.com'")
        run_command("agenthub config --show")
        
        # Step 2: Create a simple agent
        print("\n2️⃣ Creating a simple agent...")
        agent_dir = Path(temp_dir) / "demo-agent"
        run_command(f"agenthub agent init demo-agent --type simple --description 'A demo agent for testing'", cwd=temp_dir)
        
        # Step 3: Validate the agent
        print("\n3️⃣ Validating the agent...")
        run_command("agenthub agent validate", cwd=agent_dir)
        
        # Step 4: Test the agent
        print("\n4️⃣ Testing the agent...")
        run_command("agenthub agent test", cwd=agent_dir)
        run_command("agenthub agent test --input '{\"message\": \"Hello from CLI demo!\"}'", cwd=agent_dir)
        
        # Step 5: Show agent files
        print("\n5️⃣ Generated agent files:")
        for file in agent_dir.glob("*"):
            if file.is_file():
                print(f"   📄 {file.name}")
                if file.name in ["config.json", "demo_agent.py"]:
                    print(f"      Content preview:")
                    with open(file, 'r') as f:
                        lines = f.readlines()[:10]  # First 10 lines
                        for line in lines:
                            print(f"      {line.rstrip()}")
                    print("      ...")
        
        # Step 6: Dry run publish
        print("\n6️⃣ Dry run publish (validation only)...")
        run_command("agenthub agent publish --dry-run", cwd=agent_dir)
        
        # Step 7: Generate template
        print("\n7️⃣ Generating agent template...")
        template_file = Path(temp_dir) / "chat_template.py"
        run_command(f"agenthub agent template chat {template_file}")
        
        print("\n8️⃣ Template content:")
        with open(template_file, 'r') as f:
            lines = f.readlines()[:20]  # First 20 lines
            for line in lines:
                print(f"   {line.rstrip()}")
        print("   ...")
    
    print("\n✅ CLI Demo completed successfully!")
    print("\nNext steps:")
    print("1. Create your own agent: agenthub agent init my-agent")
    print("2. Customize the agent code")
    print("3. Test locally: agenthub agent test")
    print("4. Publish: agenthub agent publish")

if __name__ == "__main__":
    main() 