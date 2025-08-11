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

### SDK Installation

```bash
# Install the SDK in development mode
pip install -e ./agenthub-sdk

# Or install dependencies manually
pip install aiohttp>=3.8.0 aiofiles>=23.0.0 pydantic>=2.0.0 click>=8.0.0
```

### CLI Installation

The AgentHub SDK includes a powerful CLI tool for agent creators:

```bash
# Install CLI using the setup script
cd agent-hiring-mvp/agenthub-sdk
python setup_cli.py

# Or install manually
pip install -e .

# Verify installation
agenthub --version
agenthub --help
```

### Quick CLI Setup

```bash
# Configure your author information
agenthub config --author "Your Name" --email "your@email.com"

# Set the AgentHub server URL (if different from default)
agenthub config --base-url "https://your-agenthub-server.com"

# View current configuration
agenthub config --show
```

## Quick Start

### Using the CLI (Recommended for Beginners)

The CLI provides the easiest way to create and manage agents:

```bash
# 1. Create a new agent
agenthub agent init my-first-agent --type simple --description "My first agent"

# 2. Navigate to the agent directory
cd my-first-agent

# 3. Validate the agent
agenthub agent validate

# 4. Test the agent locally
agenthub agent test --input '{"message": "Hello, world!"}'

# 5. Publish the agent (dry run first)
agenthub agent publish --dry-run
agenthub agent publish

# 6. List available agents
agenthub agent list

# 7. Get agent information
agenthub agent info STOCK123
```

See the [CLI Guide](CLI_GUIDE.md) for comprehensive documentation.

### Using the SDK Directly

### 1. Create an Agent

The AgentHub SDK provides several agent types you can use:

#### Simple Agent
```python
from agenthub_sdk import SimpleAgent, AgentConfig

# Create agent configuration
config = AgentConfig(
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

# Create the agent
agent = SimpleAgent(config)
```

#### Data Processing Agent
```python
from agenthub_sdk import DataProcessingAgent, AgentConfig

config = AgentConfig(
    name="data-processor",
    description="Processes and analyzes data",
    version="1.0.0",
    author="Your Name",
    email="your.email@example.com",
    entry_point="data_processor.py",
    requirements=["pandas>=1.5.0", "numpy>=1.20.0"],
    tags=["data", "analytics"],
    category="data-processing",
    pricing_model="per_use",
    price_per_use=0.05
)

agent = DataProcessingAgent(config)
```

#### Chat Agent
```python
from agenthub_sdk import ChatAgent, AgentConfig

config = AgentConfig(
    name="chat-assistant",
    description="Conversational AI assistant",
    version="1.0.0",
    author="Your Name",
    email="your.email@example.com",
    entry_point="chat_agent.py",
    requirements=["openai>=1.0.0"],
    tags=["chat", "ai", "assistant"],
    category="conversational",
    pricing_model="per_use",
    price_per_use=0.02
)

agent = ChatAgent(config)
```

### 2. Generate Agent Code

The SDK can automatically generate agent code for you:

```python
import os
from agenthub_sdk import SimpleAgent, AgentConfig

# Create your agent configuration
config = AgentConfig(
    name="my-awesome-agent",
    description="A helpful agent that does amazing things",
    version="1.0.0",
    author="Your Name",
    email="your.email@example.com",
    entry_point="my_awesome_agent.py",
    requirements=["requests>=2.25.0"],
    tags=["utility", "api"],
    category="utilities",
    pricing_model="per_use",
    price_per_use=0.01
)

# Create the agent
agent = SimpleAgent(config)

# Generate and save agent code to a directory
agent.save_to_directory("./my_agent_code")
```

This will create a directory structure like:
```
my_agent_code/
├── my_awesome_agent.py  # Main agent file (entry point)
├── requirements.txt     # Python dependencies
├── README.md           # Agent documentation
└── config.json         # Agent configuration
```

### 3. Customize Agent Behavior

You can create custom agent classes by inheriting from the base classes:

```python
from agenthub_sdk import SimpleAgent, AgentConfig
from typing import Dict, Any

class CustomAgent(SimpleAgent):
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Custom message processing logic."""
        # Your custom logic here
        user_input = message.get("content", "")
        
        # Example: Echo the message with a greeting
        response = f"Hello! You said: {user_input}"
        
        return {
            "status": "success",
            "response": response,
            "message_type": "text"
        }

# Use your custom agent
config = AgentConfig(
    name="custom-echo-agent",
    description="Custom agent that echoes messages",
    version="1.0.0",
    author="Your Name",
    email="your.email@example.com",
    entry_point="custom_agent.py",
    requirements=[],
    tags=["custom", "echo"],
    category="utilities",
    pricing_model="free"
)

agent = CustomAgent(config)
```

### 4. Test Your Agent Locally

Before publishing, you should test your agent locally:

```python
import asyncio
from agenthub_sdk import SimpleAgent, AgentConfig

async def test_agent():
    # Create your agent
    config = AgentConfig(
        name="test-agent",
        description="A test agent",
        version="1.0.0",
        author="Your Name",
        email="your.email@example.com",
        entry_point="test_agent.py",
        requirements=[],
        tags=["test"],
        category="utilities",
        pricing_model="free"
    )
    
    agent = SimpleAgent(config)
    
    # Initialize the agent
    await agent.initialize({"environment": "test"})
    
    # Test message processing
    test_message = {"content": "Hello, agent!"}
    response = await agent.process_message(test_message)
    
    print(f"Agent response: {response}")
    
    # Clean up
    await agent.cleanup()

# Run the test
asyncio.run(test_agent())
```

### 5. Publish Your Agent

Once you've created your agent, you can publish it to the AgentHub platform:

```python
import asyncio
from agenthub_sdk import AgentHubClient, SimpleAgent, AgentConfig

async def publish_agent():
    # Create your agent configuration
    config = AgentConfig(
        name="my-awesome-agent",
        description="A helpful agent that does amazing things",
        version="1.0.0",
        author="Your Name",
        email="your.email@example.com",
        entry_point="my_awesome_agent.py",
        requirements=["requests>=2.25.0"],
        tags=["utility", "api"],
        category="utilities",
        pricing_model="per_use",
        price_per_use=0.01
    )
    
    # Create the agent
    agent = SimpleAgent(config)
    
    # Generate agent code directory
    agent.save_to_directory("./my_agent_code")
    
    # Connect to AgentHub and submit
    async with AgentHubClient("http://localhost:8002") as client:
        # Submit the agent
        result = await client.submit_agent(agent, "./my_agent_code/")
        print(f"Agent submitted successfully!")
        print(f"Agent ID: {result['agent_id']}")
        print(f"Status: {result['status']}")

# Run the publishing
asyncio.run(publish_agent())
```

#### Agent Approval Workflow

**Important**: After submission, agents must be approved before becoming publicly visible. Newly submitted agents have:
- `status = "submitted"`
- `is_public = False`

To approve an agent (admin only):

```bash
# Approve the agent using the admin endpoint
curl -X 'PUT' 'http://localhost:8002/api/v1/agents/{agent_id}/approve' \
     -H 'accept: application/json'
```

Once approved, the agent will have:
- `status = "approved"`
- `is_public = True`

#### Publishing with API Key (if required)

```python
async def publish_with_auth():
    # ... create agent as above ...
    
    async with AgentHubClient("http://localhost:8002") as client:
        result = await client.submit_agent(
            agent, 
            "./my_agent_code/", 
            api_key="your-api-key-here"
        )
        print(f"Agent submitted with authentication: {result}")

asyncio.run(publish_with_auth())
```

### 6. Use Published Agents

```python
import asyncio
from agenthub_sdk import AgentHubClient

async def use_agents():
    async with AgentHubClient("http://localhost:8002") as client:
        # List available agents (only approved and public agents are shown)
        agents = await client.list_agents(skip=0, limit=100)
        print(f"Found {len(agents['agents'])} agents")
        
        # Print agent details
        for agent in agents['agents']:
            print(f"- {agent['name']} (ID: {agent['id']}) - {agent['description']}")
        
        # Get details of a specific agent
        if agents['agents']:
            agent_id = agents['agents'][0]['id']  # e.g., "STOCK123", "CHAT456"
            agent_details = await client.get_agent(agent_id)
            print(f"Agent details: {agent_details}")
        
        # Hire an agent
        hire_result = await client.hire_agent(
            agent_id=agent_id,  # String ID like "STOCK123"
            config={"api_key": "your_key"},
            billing_cycle="per_use"
        )
        
        # Execute the agent
        execution_result = await client.run_agent(
            agent_id=agent_id,  # String ID like "STOCK123"
            input_data={"name": "Alice"},
            wait_for_completion=True
        )
        
        print(f"Result: {execution_result['execution']['result']}")

asyncio.run(use_agents())
```

#### Manual API Access

You can also access agents directly via the REST API:

```bash
# List all approved agents
curl -X 'GET' 'http://localhost:8002/api/v1/agents/?skip=0&limit=100' \
     -H 'accept: application/json'

# Get specific agent details
curl -X 'GET' 'http://localhost:8002/api/v1/agents/{agent_id}' \
     -H 'accept: application/json'

# Hire an agent
curl -X 'POST' 'http://localhost:8002/api/v1/hiring/hire' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
       "agent_id": 1,
       "config": {"api_key": "your_key"},
       "billing_cycle": "per_use"
     }'
```

## API Reference

### AgentConfig

Configuration class for defining agent properties:

```python
AgentConfig(
    name: str,                          # Unique agent name
    description: str,                   # Agent description
    version: str = "1.0.0",            # Version string
    author: str = "",                   # Author name
    email: str = "",                    # Author email
    entry_point: str = "",              # Main Python file
    requirements: List[str] = [],       # Python dependencies
    config_schema: Optional[Dict] = None, # JSON schema for configuration
    tags: List[str] = [],               # Search tags
    category: str = "general",          # Agent category
    pricing_model: str = "free",        # "free", "per_use", "monthly"
    price_per_use: Optional[float] = None, # Price per execution
    monthly_price: Optional[float] = None, # Monthly subscription price
    max_execution_time: int = 30,       # Maximum execution time in seconds
    memory_limit: str = "100MB"         # Memory limit for agent execution
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

#### Admin Endpoints (Direct API)

For agent management, these endpoints are available directly via the REST API:

```bash
# Approve an agent
PUT /api/v1/agents/{agent_id}/approve

# Reject an agent  
PUT /api/v1/agents/{agent_id}/reject

# Delete an agent
DELETE /api/v1/agents/{agent_id}
```

**Note**: Admin endpoints are not currently wrapped in the SDK client class.

### Synchronous Wrappers

For convenience, synchronous wrapper functions are available in the client module:

```python
from agenthub_sdk.client import submit_agent_sync, list_agents_sync, hire_agent_sync, run_agent_sync

# Submit agent
result = submit_agent_sync(agent, "my_agent/")

# List agents
agents = list_agents_sync()

# Hire agent
hire_result = hire_agent_sync(agent_id="STOCK123", config={"key": "value"})

# Run agent
execution_result = run_agent_sync(agent_id="STOCK123", input_data={"test": "data"})
```

## Examples

See the `examples/` directory for complete examples:

- `create_and_publish_agent.py` - Complete example of creating and publishing a weather agent
- `simple_agent_usage.py` - Basic agent usage patterns

## Agent Development Guidelines

### 1. Agent Structure

When using the SDK's automatic code generation, your agent directory will have this structure:

```
agent_directory/
├── agent_name.py     # Entry point (generated automatically)
├── requirements.txt  # Dependencies (generated automatically)
├── README.md        # Documentation (generated automatically)
└── config.json      # Agent configuration (generated automatically)
```

### 2. Manual Agent Development

If you prefer to create agent code manually, you can inherit from the agent base classes:

```python
from agenthub_sdk import Agent, AgentConfig
from typing import Dict, Any

class MyCustomAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        # Your initialization code here
    
    async def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the agent with context."""
        # Setup code here
        pass
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        # Your message processing logic here
        return {"status": "success", "response": "Message processed"}
    
    async def cleanup(self) -> None:
        """Clean up resources when the agent is done."""
        # Cleanup code here
        pass
    
    def generate_code(self) -> str:
        """Generate the agent code as a string."""
        return '''
def main(input_data, config):
    # Your main function logic here
    return {"result": "success"}
'''
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
   ```bash
   pip install -r requirements.txt
   ```

2. **Validation Errors**: Check your `AgentConfig` for required fields
   ```python
   # Validate your config
   config = AgentConfig(...)
   errors = config.validate()
   if errors:
       print(f"Validation errors: {errors}")
   ```

3. **Agent Not Visible After Submission**: Agents need approval before becoming public
   ```bash
   # Check if agent was created (replace {agent_id} with actual ID from submission)
   curl -X 'GET' 'http://localhost:8002/api/v1/agents/{agent_id}' -H 'accept: application/json'
   
   # If you get 404, the agent needs approval:
   curl -X 'PUT' 'http://localhost:8002/api/v1/agents/{agent_id}/approve' -H 'accept: application/json'
   ```

4. **Empty Agent List**: Use correct API endpoint with query parameters
   ```bash
   # ✅ Correct - includes query parameters
   curl -X 'GET' 'http://localhost:8002/api/v1/agents/?skip=0&limit=100' -H 'accept: application/json'
   
   # ❌ Incorrect - missing query parameters (returns redirect)
   curl -X 'GET' 'http://localhost:8002/api/v1/agents' -H 'accept: application/json'
   ```

5. **Execution Errors**: Test your agent locally first
   ```python
   # Test locally before publishing
   await agent.initialize({})
   response = await agent.process_message({"content": "test"})
   print(response)
   ```

6. **Network Errors**: Ensure the AgentHub server is running and accessible
   ```python
   # Check server connectivity
   async with AgentHubClient("http://localhost:8002") as client:
       is_healthy = await client.health_check()
       print(f"Server healthy: {is_healthy}")
   ```

7. **Package Installation Issues**: If you see setup.py or pyproject.toml errors:
   ```bash
   # Make sure you're in the correct directory
   pip install -e ./agenthub-sdk
   ```

### Getting Help

- Check the server logs for detailed error messages
- Validate your agent configuration before submission
- Test your agent code independently
- Use the health check to verify server connectivity
- Check the examples directory for working code samples

## CLI Commands Reference

The AgentHub CLI provides comprehensive commands for agent creators:

### Agent Management Commands

```bash
# Create a new agent project
agenthub agent init <name> [OPTIONS]

# Validate agent configuration and code
agenthub agent validate [--directory DIR]

# Test agent locally
agenthub agent test [--input JSON] [--config JSON]

# Publish agent to platform
agenthub agent publish [--dry-run] [--api-key KEY]

# List available agents
agenthub agent list [--query QUERY] [--category CATEGORY]

# Get agent information
agenthub agent info <agent-id>

# Generate agent templates
agenthub agent template <type> <output-file>
```

### Configuration Commands

```bash
# Configure CLI settings
agenthub config [--author NAME] [--email EMAIL] [--base-url URL] [--api-key KEY]

# Show current configuration
agenthub config --show
```

### Example Workflows

```bash
# Create and publish a simple agent
agenthub agent init my-agent --type simple
cd my-agent
agenthub agent validate
agenthub agent test
agenthub agent publish --dry-run
agenthub agent publish

# Create a data processing agent
agenthub agent init data-processor --type data --category analytics --pricing per_use --price 0.10

# Create a chat agent
agenthub agent init chat-bot --type chat --category support --pricing monthly --price 29.99
```

For detailed CLI documentation, see the [CLI Guide](CLI_GUIDE.md).

## Complete Agent Workflow

The AgentHub platform follows a complete lifecycle for agent management:

### 1. Development Phase
- **Create Agent**: Use SDK to define agent configuration
- **Generate Code**: Automatically generate agent code directory
- **Test Locally**: Validate agent behavior before submission

### 2. Submission Phase
- **Submit Agent**: Upload agent to platform via SDK
- **Validation**: Platform validates agent code and configuration
- **Status**: Agent created with `status="submitted"` and `is_public=false`

### 3. Approval Phase (Admin)
- **Review**: Admin reviews submitted agent
- **Approve**: Use `/agents/{id}/approve` endpoint
- **Publication**: Agent becomes `status="approved"` and `is_public=true`

### 4. Usage Phase
- **Discovery**: Users can find agents via `/agents/?skip=0&limit=100`
- **Hiring**: Users hire agents for their use cases
- **Execution**: Agents execute tasks and return results

## Summary

The AgentHub SDK provides a comprehensive platform for creating, testing, and publishing AI agents. Key features include:

- **Multiple Agent Types**: SimpleAgent, DataProcessingAgent, ChatAgent
- **Automatic Code Generation**: Generate complete agent directories
- **Approval Workflow**: Secure agent review and approval process
- **Easy Publishing**: Submit agents to the platform with validation
- **Local Testing**: Test agents before publishing
- **Async/Sync Support**: Both asynchronous and synchronous interfaces

Get started by creating your first agent and following the step-by-step guide above!

## License

This SDK is part of the AgentHub platform. See the main project license for details. 