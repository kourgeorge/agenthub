# AgentHub SDK

A comprehensive SDK for creating, publishing, and using AI agents on the AgentHub platform.

## Features

- **Agent Creation**: Easy-to-use classes for defining agent configurations
- **Agent Publishing**: Submit agents to the platform with automatic validation
- **Agent Discovery**: Browse and search available agents
- **Agent Hiring**: Hire agents for your use cases
- **Agent Execution**: Execute agents with full lifecycle management
- **Async & Sync APIs**: Both asynchronous and synchronous interfaces

## Installation

```bash
# Install the SDK dependencies
pip install aiohttp aiofiles pydantic

# Or install from the SDK directory
cd agenthub-sdk
pip install -r requirements.txt
```

## Quick Start

### 1. Create an Agent

```python
from agenthub_sdk import Agent, AgentConfig

class MyAgent(Agent):
    def __init__(self):
        super().__init__()
        
        # Configure your agent
        self.config = AgentConfig(
            name="my-awesome-agent",
            description="A helpful agent that does amazing things",
            version="1.0.0",
            author="Your Name",
            email="your.email@example.com",
            entry_point="my_agent.py",
            requirements=["requests>=2.25.0"],
            tags=["utility", "api"],
            category="utilities",
            pricing_model="per_use",
            price_per_use=0.01
        )
    
    def get_config(self) -> AgentConfig:
        return self.config
    
    def process(self, input_data: dict, config: dict = None) -> dict:
        # Your agent logic here
        return {"result": "Hello from my agent!"}
```

### 2. Create Agent Code

Create a directory with your agent code:

```
my_agent/
├── my_agent.py          # Main agent file (entry point)
├── requirements.txt     # Python dependencies
└── README.md           # Agent documentation
```

Example `my_agent.py`:

```python
#!/usr/bin/env python3
"""
My Awesome Agent - Does amazing things!
"""

import json
from typing import Dict, Any

def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input
        config: Agent configuration
    
    Returns:
        Agent response
    """
    # Your agent logic here
    name = input_data.get("name", "World")
    return {
        "message": f"Hello, {name}!",
        "status": "success"
    }

if __name__ == "__main__":
    # Test the agent
    test_input = {"name": "Test User"}
    test_config = {}
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
```

### 3. Publish Your Agent

```python
import asyncio
from agenthub_sdk import AgentHubClient

async def publish_agent():
    # Create your agent
    agent = MyAgent()
    
    # Connect to AgentHub
    async with AgentHubClient("http://localhost:8002") as client:
        # Submit the agent
        result = await client.submit_agent(agent, "my_agent/")
        print(f"Agent submitted! ID: {result['agent_id']}")

# Run the publishing
asyncio.run(publish_agent())
```

### 4. Use Published Agents

```python
import asyncio
from agenthub_sdk import AgentHubClient

async def use_agents():
    async with AgentHubClient("http://localhost:8002") as client:
        # List available agents
        agents = await client.list_agents()
        print(f"Found {len(agents['agents'])} agents")
        
        # Hire an agent
        agent_id = 1
        hire_result = await client.hire_agent(
            agent_id=agent_id,
            config={"api_key": "your_key"},
            billing_cycle="per_use"
        )
        
        # Execute the agent
        execution_result = await client.run_agent(
            agent_id=agent_id,
            input_data={"name": "Alice"},
            wait_for_completion=True
        )
        
        print(f"Result: {execution_result['execution']['result']}")

asyncio.run(use_agents())
```

## API Reference

### AgentConfig

Configuration class for defining agent properties:

```python
AgentConfig(
    name: str,                    # Unique agent name
    description: str,             # Agent description
    version: str,                 # Version string
    author: str,                  # Author name
    email: str,                   # Author email
    entry_point: str,             # Main Python file
    requirements: List[str],      # Python dependencies
    config_schema: Dict,          # JSON schema for configuration
    tags: List[str],              # Search tags
    category: str,                # Agent category
    pricing_model: str,           # "per_use" or "monthly"
    price_per_use: float,         # Price per execution
    monthly_price: float          # Monthly subscription price
)
```

### AgentHubClient

Main client class for platform interactions:

#### Agent Submission
- `submit_agent(agent, code_directory, api_key=None)` - Submit an agent

#### Agent Discovery
- `list_agents(skip=0, limit=100, query=None, category=None)` - List agents
- `get_agent(agent_id)` - Get agent details

#### Agent Hiring
- `hire_agent(agent_id, config=None, billing_cycle=None, user_id=None)` - Hire an agent
- `list_hired_agents(user_id=None)` - List hired agents

#### Agent Execution
- `execute_agent(agent_id, input_data, hiring_id=None, user_id=None)` - Execute agent
- `get_execution_status(execution_id)` - Get execution status
- `run_agent(agent_id, input_data, hiring_id=None, user_id=None, wait_for_completion=True, timeout=60)` - Run and wait for completion

### Synchronous Wrappers

For convenience, synchronous wrapper functions are available:

```python
from agenthub_sdk import submit_agent_sync, list_agents_sync, hire_agent_sync, run_agent_sync

# Submit agent
result = submit_agent_sync(agent, "my_agent/")

# List agents
agents = list_agents_sync()

# Hire agent
hire_result = hire_agent_sync(agent_id=1, config={"key": "value"})

# Run agent
execution_result = run_agent_sync(agent_id=1, input_data={"test": "data"})
```

## Examples

See the `examples/` directory for complete examples:

- `create_and_publish_agent.py` - Complete example of creating and publishing a weather agent
- `simple_agent_usage.py` - Basic agent usage patterns

## Agent Development Guidelines

### 1. Agent Structure

Your agent code should follow this structure:

```
agent_directory/
├── main_agent.py      # Entry point (required)
├── requirements.txt   # Dependencies (required)
├── README.md         # Documentation (recommended)
└── other_files.py    # Additional modules
```

### 2. Entry Point Function

Your main agent file must have a `main` function with this signature:

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input data
        config: Agent configuration
    
    Returns:
        Agent response (must be JSON serializable)
    """
    # Your logic here
    return {"result": "success"}
```

### 3. Error Handling

Always handle errors gracefully:

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Your logic here
        return {"result": "success", "data": result}
    except Exception as e:
        return {"error": str(e), "status": "failed"}
```

### 4. Configuration Schema

Define a JSON schema for your agent's configuration:

```python
config_schema = {
    "type": "object",
    "properties": {
        "api_key": {
            "type": "string",
            "description": "API key for external service"
        },
        "timeout": {
            "type": "integer",
            "default": 30,
            "description": "Request timeout in seconds"
        }
    },
    "required": ["api_key"]
}
```

## Testing

Test your agent locally before publishing:

```python
# Test the agent function directly
from my_agent import main

test_input = {"test": "data"}
test_config = {"api_key": "test_key"}

result = main(test_input, test_config)
print(result)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are in `requirements.txt`
2. **Validation Errors**: Check your `AgentConfig` for required fields
3. **Execution Errors**: Test your agent locally first
4. **Network Errors**: Ensure the AgentHub server is running and accessible

### Getting Help

- Check the server logs for detailed error messages
- Validate your agent configuration before submission
- Test your agent code independently
- Use the health check to verify server connectivity

## License

This SDK is part of the AgentHub platform. See the main project license for details. 