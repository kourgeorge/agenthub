# Agent Creation and Publishing Guide

This guide shows you how to create and publish agents to the AgentHub platform using both the SDK and manual methods.

## Overview

The AgentHub platform allows you to:
1. **Create agents** with custom logic and configuration
2. **Publish agents** to the platform for others to discover
3. **Hire agents** for your specific use cases
4. **Execute agents** with custom input data

## Method 1: Using the AgentHub SDK (Recommended)

The SDK provides a clean, type-safe interface for creating and publishing agents.

### Installation

```bash
# Install SDK dependencies
pip install aiohttp aiofiles pydantic

# Or install from the SDK directory
cd agenthub-sdk
pip install -r requirements.txt
```

### Quick Example

```python
import asyncio
import tempfile
from pathlib import Path

# Add SDK to path
import sys
sys.path.insert(0, "agenthub-sdk")

from agenthub_sdk.agent import Agent, AgentConfig
from agenthub_sdk.client import AgentHubClient

class MyAgent(Agent):
    def __init__(self):
        super().__init__()
        
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
        return {"result": "Hello from my agent!"}

async def publish_agent():
    # Create agent code directory
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_dir = Path(temp_dir) / "my_agent"
        agent_dir.mkdir()
        
        # Create agent code
        agent_code = '''
import json
from typing import Dict, Any

def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    name = input_data.get("name", "World")
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    result = main({"name": "Test"}, {})
    print(json.dumps(result, indent=2))
'''
        
        with open(agent_dir / "my_agent.py", "w") as f:
            f.write(agent_code)
        
        # Create requirements.txt
        with open(agent_dir / "requirements.txt", "w") as f:
            f.write("# No external dependencies\n")
        
        # Create and submit agent
        agent = MyAgent()
        
        async with AgentHubClient("http://localhost:8002") as client:
            result = await client.submit_agent(agent, str(agent_dir))
            print(f"Agent submitted! ID: {result['agent_id']}")

# Run the publishing
asyncio.run(publish_agent())
```

### SDK Features

- **Agent Configuration**: Easy-to-use `AgentConfig` class
- **Validation**: Automatic validation of agent configuration
- **Async/Sync APIs**: Both asynchronous and synchronous interfaces
- **Error Handling**: Comprehensive error handling and reporting
- **Type Safety**: Full type hints and validation

## Method 2: Manual Agent Creation

You can also create agents manually without the SDK.

### Agent Structure

Your agent should have this directory structure:

```
my_agent/
├── my_agent.py          # Main agent file (required)
├── requirements.txt     # Python dependencies (required)
├── README.md           # Documentation (recommended)
└── other_files.py      # Additional modules (optional)
```

### Agent Code Template

```python
#!/usr/bin/env python3
"""
My Agent - Description of what your agent does.
"""

import json
from typing import Dict, Any

def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input data
        config: Agent configuration
    
    Returns:
        Agent response (must be JSON serializable)
    """
    try:
        # Your agent logic here
        name = input_data.get("name", "World")
        result = {"message": f"Hello, {name}!"}
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

# For testing
if __name__ == "__main__":
    test_input = {"name": "Test User"}
    test_config = {}
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
```

### Manual Submission

```python
import json
import zipfile
import requests
from pathlib import Path

def create_agent_zip(agent_dir: str) -> str:
    """Create a ZIP file from the agent directory."""
    agent_path = Path(agent_dir)
    zip_path = agent_path.parent / "agent.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in agent_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(agent_path)
                zip_file.write(file_path, relative_path)
    
    return str(zip_path)

def submit_agent(agent_zip_path: str, base_url: str = "http://localhost:8002"):
    """Submit the agent to the platform."""
    
    # Agent configuration
    agent_config = {
        "name": "my-agent",
        "description": "A helpful agent",
        "version": "1.0.0",
        "author": "Your Name",
        "email": "your.email@example.com",
        "entry_point": "my_agent.py",
        "requirements": [],
        "tags": ["demo"],
        "category": "utilities",
        "pricing_model": "per_use",
        "price_per_use": 0.01
    }
    
    # Submit to platform
    with open(agent_zip_path, 'rb') as f:
        files = {'code_file': ('agent.zip', f, 'application/zip')}
        data = {k: str(v) if not isinstance(v, list) else json.dumps(v) 
                for k, v in agent_config.items()}
        
        response = requests.post(
            f"{base_url}/api/v1/agents/submit",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Submission failed: {response.text}")

# Usage
agent_dir = "my_agent/"
zip_path = create_agent_zip(agent_dir)
result = submit_agent(zip_path)
print(f"Agent submitted! ID: {result['agent_id']}")
```

## Agent Configuration

### Required Fields

- `name`: Unique agent name (lowercase, hyphens allowed)
- `description`: Clear description of what the agent does
- `version`: Semantic version (e.g., "1.0.0")
- `author`: Your name or organization
- `email`: Contact email
- `entry_point`: Main Python file (e.g., "my_agent.py")

### Optional Fields

- `requirements`: List of Python dependencies
- `config_schema`: JSON schema for agent configuration
- `tags`: List of search tags
- `category`: Agent category (e.g., "utilities", "ai", "data")
- `pricing_model`: "per_use" or "monthly"
- `price_per_use`: Price per execution
- `monthly_price`: Monthly subscription price

### Configuration Schema Example

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

## Testing Your Agent

### Local Testing

Always test your agent locally before publishing:

```python
# Test the agent function directly
from my_agent import main

test_input = {"name": "Alice"}
test_config = {"api_key": "test_key"}

result = main(test_input, test_config)
print(json.dumps(result, indent=2))
```

### Platform Testing

After publishing, test on the platform:

```python
import requests

# Hire the agent
hire_data = {
    "agent_id": 1,
    "config": {"api_key": "your_key"},
    "billing_cycle": "per_use"
}

hire_response = requests.post(
    "http://localhost:8002/api/v1/hiring/hire/1",
    json=hire_data
)

# Execute the agent
execution_data = {
    "agent_id": 1,
    "input_data": {"name": "World"}
}

exec_response = requests.post(
    "http://localhost:8002/api/v1/execution",
    json=execution_data
)

print(exec_response.json())
```

## Best Practices

### 1. Agent Design

- **Single Responsibility**: Each agent should do one thing well
- **Clear Interface**: Define clear input/output formats
- **Error Handling**: Always handle errors gracefully
- **Documentation**: Provide clear documentation and examples

### 2. Code Quality

- **Type Hints**: Use type hints for better code clarity
- **Validation**: Validate input data and configuration
- **Testing**: Test your agent thoroughly before publishing
- **Dependencies**: Minimize external dependencies

### 3. Security

- **Input Validation**: Validate all input data
- **Resource Limits**: Be mindful of resource usage
- **Error Messages**: Don't expose sensitive information in errors
- **Dependencies**: Use trusted, well-maintained packages

### 4. Performance

- **Efficient Algorithms**: Use efficient algorithms and data structures
- **Caching**: Cache results when appropriate
- **Async Operations**: Use async operations for I/O-bound tasks
- **Resource Management**: Clean up resources properly

## Examples

### Complete Examples

See the `examples/` directory for complete working examples:

- `complete_agent_workflow.py` - Manual agent creation and publishing
- `simple_agent_example.py` - SDK-based agent creation (when dependencies are available)

### Agent Types

Here are some example agent types you can create:

1. **Utility Agents**
   - Calculator agents
   - Text processing agents
   - File conversion agents

2. **API Wrapper Agents**
   - Weather data agents
   - News aggregation agents
   - Translation agents

3. **Data Processing Agents**
   - CSV processing agents
   - Image processing agents
   - Data validation agents

4. **AI/ML Agents**
   - Text generation agents
   - Image classification agents
   - Sentiment analysis agents

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Make sure all dependencies are in `requirements.txt`
   - Test imports locally before publishing

2. **Validation Errors**
   - Check your `AgentConfig` for required fields
   - Validate JSON schemas

3. **Execution Errors**
   - Test your agent locally first
   - Check server logs for detailed errors

4. **Network Errors**
   - Ensure the server is running and accessible
   - Check firewall and network settings

### Getting Help

- Check the server logs for detailed error messages
- Validate your agent configuration before submission
- Test your agent code independently
- Use the health check endpoint to verify server connectivity

## Next Steps

After creating and publishing your agent:

1. **Monitor Usage**: Check agent usage and performance
2. **Gather Feedback**: Collect user feedback and improve
3. **Update Regularly**: Keep your agent updated with new features
4. **Scale**: Consider scaling options for high-demand agents

## API Reference

### Agent Submission Endpoint

```
POST /api/v1/agents/submit
Content-Type: multipart/form-data

Fields:
- code_file: ZIP file containing agent code
- name: Agent name
- description: Agent description
- version: Version string
- author: Author name
- email: Author email
- entry_point: Main Python file
- requirements: JSON array of dependencies
- config_schema: JSON schema for configuration
- tags: JSON array of tags
- category: Agent category
- pricing_model: Pricing model
- price_per_use: Price per use
- monthly_price: Monthly price
```

### Agent Execution Endpoint

```
POST /api/v1/execution
Content-Type: application/json

{
    "agent_id": 1,
    "input_data": {"key": "value"},
    "hiring_id": 123
}
```

### Agent Status Endpoint

```
GET /api/v1/execution/{execution_id}
```

For more detailed API documentation, see the server's Swagger UI at `http://localhost:8002/docs`. 