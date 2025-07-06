#!/usr/bin/env python3
"""
Simple Agent Creation Example

This example shows how to create and publish a simple agent using the AgentHub SDK.
Run this example with:
    python examples/simple_agent_example.py
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add the SDK to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "agenthub-sdk"))

# Import the SDK components
try:
    from agenthub_sdk.agent import Agent, AgentConfig
    from agenthub_sdk.client import AgentHubClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have installed the SDK dependencies:")
    print("pip install aiohttp aiofiles pydantic")
    sys.exit(1)


class SimpleGreetingAgent(Agent):
    """A simple agent that greets users."""
    
    def __init__(self):
        super().__init__()
        
        # Configure the agent
        self.config = AgentConfig(
            name="simple-greeting-agent",
            description="A friendly agent that greets users with customizable messages",
            version="1.0.0",
            author="AgentHub Demo",
            email="demo@agenthub.com",
            entry_point="greeting_agent.py",
            requirements=[],
            config_schema={
                "type": "object",
                "properties": {
                    "greeting_style": {
                        "type": "string",
                        "enum": ["formal", "casual", "friendly"],
                        "default": "friendly",
                        "description": "Style of greeting to use"
                    },
                    "include_time": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to include time in greeting"
                    }
                }
            },
            tags=["greeting", "demo", "simple"],
            category="utilities",
            pricing_model="per_use",
            price_per_use=0.001,
            monthly_price=None
        )
    
    def get_config(self) -> AgentConfig:
        return self.config
    
    def process(self, input_data: dict, config: dict = None) -> dict:
        """Process greeting requests."""
        # This is just a placeholder - the actual logic will be in the agent code
        return {"message": "Greeting logic implemented in agent code"}


def create_agent_code(directory: str):
    """Create the agent code files."""
    agent_dir = Path(directory)
    
    # Create the main agent file
    agent_code = '''#!/usr/bin/env python3
"""
Simple Greeting Agent - Greets users with customizable messages.
"""

import json
from datetime import datetime
from typing import Dict, Any


def get_greeting_style(style: str) -> str:
    """Get greeting based on style."""
    greetings = {
        "formal": "Good day",
        "casual": "Hey",
        "friendly": "Hello"
    }
    return greetings.get(style, "Hello")


def get_time_greeting() -> str:
    """Get time-based greeting."""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Good night"


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input containing name and optional message
        config: Agent configuration (greeting style, include time)
    
    Returns:
        Greeting message
    """
    try:
        # Get configuration
        greeting_style = config.get("greeting_style", "friendly")
        include_time = config.get("include_time", True)
        
        # Get input data
        name = input_data.get("name", "there")
        custom_message = input_data.get("message", "")
        
        # Build greeting
        if include_time:
            base_greeting = get_time_greeting()
        else:
            base_greeting = get_greeting_style(greeting_style)
        
        greeting = f"{base_greeting}, {name}!"
        
        # Add custom message if provided
        if custom_message:
            greeting += f" {custom_message}"
        
        return {
            "greeting": greeting,
            "style": greeting_style,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "error": f"Failed to generate greeting: {str(e)}",
            "status": "error"
        }


# For testing
if __name__ == "__main__":
    # Test the agent
    test_input = {
        "name": "Alice",
        "message": "How are you today?"
    }
    
    test_config = {
        "greeting_style": "friendly",
        "include_time": True
    }
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    # Write the agent code
    with open(agent_dir / "greeting_agent.py", "w") as f:
        f.write(agent_code)
    
    # Create requirements.txt (empty for this simple agent)
    with open(agent_dir / "requirements.txt", "w") as f:
        f.write("# No external dependencies required\n")
    
    # Create README.md
    readme = '''# Simple Greeting Agent

A friendly agent that greets users with customizable messages.

## Features

- Customizable greeting styles (formal, casual, friendly)
- Time-based greetings
- Custom message support
- No external dependencies

## Usage

The agent accepts the following input format:

```json
{
    "name": "Alice",
    "message": "How are you today?"
}
```

## Configuration

- `greeting_style` (optional): "formal", "casual", or "friendly" (default: "friendly")
- `include_time` (optional): Whether to include time-based greeting (default: true)

## Example Response

```json
{
    "greeting": "Good morning, Alice! How are you today?",
    "style": "friendly",
    "timestamp": "2024-01-15T09:30:00",
    "status": "success"
}
```
'''
    
    with open(agent_dir / "README.md", "w") as f:
        f.write(readme)


async def main():
    """Main example function."""
    print("👋 Simple Greeting Agent Example")
    print("=" * 40)
    
    # Create a temporary directory for the agent code
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Created temporary directory: {temp_dir}")
        
        # Create the agent code
        create_agent_code(temp_dir)
        print("📝 Created agent code files")
        
        # Create the agent instance
        agent = SimpleGreetingAgent()
        print("🤖 Created agent instance")
        
        # Validate the agent configuration
        config = agent.get_config()
        errors = config.validate()
        if errors:
            print(f"❌ Agent validation failed: {errors}")
            return
        
        print("✅ Agent configuration is valid")
        
        # Connect to the AgentHub platform
        base_url = "http://localhost:8002"
        print(f"🔗 Connecting to AgentHub at: {base_url}")
        
        try:
            async with AgentHubClient(base_url) as client:
                # Check if server is healthy
                if not await client.health_check():
                    print("❌ Server is not responding. Make sure the server is running.")
                    print("Start the server with: python server/main.py")
                    return
                
                print("✅ Server is healthy")
                
                # Submit the agent
                print("📤 Submitting agent to platform...")
                result = await client.submit_agent(agent, temp_dir)
                print(f"✅ Agent submitted successfully!")
                print(f"   Agent ID: {result.get('agent_id')}")
                print(f"   Status: {result.get('status')}")
                
                # List available agents to confirm
                print("\n📋 Listing available agents...")
                agents_result = await client.list_agents()
                agents = agents_result.get("agents", [])
                
                if agents:
                    print(f"Found {len(agents)} agents:")
                    for agent_info in agents:
                        print(f"  - {agent_info['name']} (ID: {agent_info['id']}) - {agent_info['status']}")
                else:
                    print("No agents found")
                
                # Test hiring the agent
                print("\n💼 Testing agent hiring...")
                agent_id = result.get("agent_id")
                if agent_id:
                    hire_result = await client.hire_agent(
                        agent_id=agent_id,
                        config={"greeting_style": "friendly", "include_time": True},
                        billing_cycle="per_use"
                    )
                    print(f"✅ Agent hired successfully!")
                    print(f"   Hiring ID: {hire_result.get('hiring_id')}")
                    
                    # Test execution
                    print("\n🚀 Testing agent execution...")
                    execution_result = await client.run_agent(
                        agent_id=agent_id,
                        input_data={
                            "name": "World",
                            "message": "Welcome to AgentHub!"
                        },
                        wait_for_completion=True,
                        timeout=30
                    )
                    
                    execution = execution_result.get("execution", {})
                    print(f"✅ Execution completed!")
                    print(f"   Status: {execution.get('status')}")
                    print(f"   Result: {execution.get('result', 'No result')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure the server is running on port 8002")
            print("2. Check that all dependencies are installed")
            print("3. Verify the server is accessible")
            return
        
        print("\n🎉 Example completed successfully!")
        print("\nNext steps:")
        print("1. The agent is now available on the platform")
        print("2. Users can hire and execute the agent")
        print("3. You can view the agent in the web interface")
        print("4. The agent will need approval before being publicly available")


if __name__ == "__main__":
    asyncio.run(main()) 