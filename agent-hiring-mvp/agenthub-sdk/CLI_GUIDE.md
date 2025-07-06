# AgentHub CLI Guide

The AgentHub CLI is a powerful command-line tool designed for agent creators to streamline the process of building, testing, and publishing AI agents.

## Installation

### Quick Installation

```bash
cd agent-hiring-mvp/agenthub-sdk
python setup_cli.py
```

### Manual Installation

```bash
cd agent-hiring-mvp/agenthub-sdk
pip install -e .
```

### Verify Installation

```bash
agenthub --help
agenthub --version
```

## Configuration

Before creating agents, configure your default settings:

```bash
# Set up your author information
agenthub config --author "Your Name" --email "your@email.com"

# Configure the AgentHub server (if different from default)
agenthub config --base-url "https://your-agenthub-server.com"

# Set your API key for publishing
agenthub config --api-key "your-api-key"

# View current configuration
agenthub config --show
```

## Quick Start

### 1. Create a New Agent

```bash
# Create a simple agent
agenthub agent init my-first-agent --type simple

# Create a data processing agent
agenthub agent init data-processor --type data --category "analytics"

# Create a chat agent
agenthub agent init chat-bot --type chat --pricing per_use --price 0.05
```

### 2. Navigate to Your Agent Directory

```bash
cd my-first-agent
```

### 3. Validate Your Agent

```bash
agenthub agent validate
```

### 4. Test Your Agent Locally

```bash
# Test with default input
agenthub agent test

# Test with custom input
agenthub agent test --input '{"message": "Hello, world!"}'

# Test with custom config
agenthub agent test --config '{"debug": true}'
```

### 5. Publish Your Agent

```bash
# Dry run (validate without publishing)
agenthub agent publish --dry-run

# Publish to the platform
agenthub agent publish
```

## Commands Reference

### Agent Commands

#### `agenthub agent init`

Create a new agent project with boilerplate code.

```bash
agenthub agent init NAME [OPTIONS]
```

**Options:**
- `--type, -t`: Agent type (simple, data, chat) [default: simple]
- `--author, -a`: Agent author name
- `--email, -e`: Agent author email
- `--description, -d`: Agent description
- `--category, -c`: Agent category [default: general]
- `--pricing, -p`: Pricing model (free, per_use, monthly) [default: free]
- `--price`: Price per use or monthly price
- `--tags`: Comma-separated tags
- `--directory, -dir`: Target directory

**Examples:**
```bash
# Basic agent
agenthub agent init my-agent

# Advanced agent with options
agenthub agent init "Data Analyzer" \
  --type data \
  --author "Jane Doe" \
  --email "jane@example.com" \
  --description "Analyzes CSV data and generates insights" \
  --category "analytics" \
  --pricing per_use \
  --price 0.10 \
  --tags "data,analysis,csv"

# Chat agent
agenthub agent init "Support Bot" \
  --type chat \
  --category "support" \
  --pricing monthly \
  --price 29.99
```

#### `agenthub agent validate`

Validate agent configuration and code.

```bash
agenthub agent validate [OPTIONS]
```

**Options:**
- `--directory, -dir`: Agent directory to validate [default: .]

**Examples:**
```bash
# Validate current directory
agenthub agent validate

# Validate specific directory
agenthub agent validate --directory /path/to/my-agent
```

#### `agenthub agent test`

Test agent locally with sample data.

```bash
agenthub agent test [OPTIONS]
```

**Options:**
- `--directory, -dir`: Agent directory to test [default: .]
- `--input, -i`: JSON input data for testing
- `--config, -c`: JSON config data for testing

**Examples:**
```bash
# Test with default input
agenthub agent test

# Test with custom input
agenthub agent test --input '{"message": "Hello, test!"}'

# Test data processing agent
agenthub agent test --input '{"data": [1,2,3,4,5], "operation": "sum"}'

# Test with configuration
agenthub agent test --config '{"debug": true, "verbose": true}'
```

#### `agenthub agent publish`

Publish agent to the AgentHub platform.

```bash
agenthub agent publish [OPTIONS]
```

**Options:**
- `--directory, -dir`: Agent directory to publish [default: .]
- `--api-key`: API key for authentication
- `--base-url`: Base URL of the AgentHub server
- `--dry-run`: Validate without publishing

**Examples:**
```bash
# Publish current directory
agenthub agent publish

# Dry run (validate only)
agenthub agent publish --dry-run

# Publish with specific API key
agenthub agent publish --api-key "your-api-key"

# Publish to different server
agenthub agent publish --base-url "https://staging.agenthub.com"
```

#### `agenthub agent list`

List available agents on the platform.

```bash
agenthub agent list [OPTIONS]
```

**Options:**
- `--query, -q`: Search query
- `--category, -c`: Filter by category
- `--limit, -l`: Number of results to show [default: 10]
- `--base-url`: Base URL of the AgentHub server

**Examples:**
```bash
# List all agents
agenthub agent list

# Search for agents
agenthub agent list --query "data analysis"

# Filter by category
agenthub agent list --category "analytics"

# Limit results
agenthub agent list --limit 5
```

#### `agenthub agent info`

Get detailed information about a specific agent.

```bash
agenthub agent info AGENT_ID [OPTIONS]
```

**Options:**
- `--base-url`: Base URL of the AgentHub server

**Examples:**
```bash
# Get agent info
agenthub agent info 123

# Get agent info from different server
agenthub agent info 123 --base-url "https://staging.agenthub.com"
```

#### `agenthub agent template`

Generate agent template code.

```bash
agenthub agent template TEMPLATE_TYPE OUTPUT_FILE
```

**Arguments:**
- `TEMPLATE_TYPE`: Type of template (simple, data, chat)
- `OUTPUT_FILE`: Output file path

**Examples:**
```bash
# Generate simple agent template
agenthub agent template simple my_agent.py

# Generate data processing template
agenthub agent template data data_processor.py

# Generate chat agent template
agenthub agent template chat chat_bot.py
```

### Configuration Commands

#### `agenthub config`

Configure CLI settings.

```bash
agenthub config [OPTIONS]
```

**Options:**
- `--base-url`: Base URL of the AgentHub server
- `--api-key`: API key for authentication
- `--author`: Default author name
- `--email`: Default email address
- `--show`: Show current configuration

**Examples:**
```bash
# Show current config
agenthub config --show

# Set author and email
agenthub config --author "John Doe" --email "john@example.com"

# Set server URL
agenthub config --base-url "https://my-agenthub.com"

# Set API key
agenthub config --api-key "your-secret-key"
```

## Agent Types

### Simple Agent

A basic agent that processes input and returns output.

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    message = input_data.get("message", "Hello")
    return {"response": f"Processed: {message}"}
```

**Use cases:**
- Text processing
- API integrations
- Simple transformations

### Data Processing Agent

An agent specialized for data analysis and manipulation.

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    data = input_data.get("data", [])
    operation = input_data.get("operation", "count")
    
    if operation == "sum":
        result = sum(data)
    elif operation == "count":
        result = len(data)
    
    return {"result": result}
```

**Use cases:**
- Data analysis
- Statistical calculations
- Data transformations
- Report generation

### Chat Agent

An agent designed for conversational interactions.

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    message = input_data.get("message", "")
    history = input_data.get("conversation_history", [])
    
    # Generate response based on message
    response = generate_response(message, history)
    
    return {"response": response}
```

**Use cases:**
- Customer support
- Virtual assistants
- Interactive tutorials
- Q&A systems

## Best Practices

### 1. Agent Structure

```
my-agent/
├── my_agent.py         # Main agent code
├── config.json         # Agent configuration
├── requirements.txt    # Dependencies
├── README.md          # Documentation
├── .gitignore         # Git ignore file
└── test_data/         # Test data (optional)
    ├── input.json
    └── expected_output.json
```

### 2. Error Handling

Always include proper error handling in your agents:

```python
def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Your agent logic here
        result = process_data(input_data)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 3. Configuration Schema

Define a configuration schema for your agents:

```json
{
  "config_schema": {
    "type": "object",
    "properties": {
      "debug": {"type": "boolean", "default": false},
      "max_items": {"type": "integer", "default": 100}
    }
  }
}
```

### 4. Testing

Test your agents thoroughly before publishing:

```bash
# Test with various inputs
agenthub agent test --input '{"message": "test1"}'
agenthub agent test --input '{"message": "test2", "options": {"verbose": true}}'

# Test error conditions
agenthub agent test --input '{}'
agenthub agent test --input '{"invalid": "data"}'
```

### 5. Documentation

Include comprehensive documentation:

- Clear description of what the agent does
- Input/output format examples
- Configuration options
- Usage examples
- Error handling information

## Troubleshooting

### Common Issues

#### "No config.json found"
```bash
# Run init first
agenthub agent init my-agent
cd my-agent
```

#### "Agent validation failed"
```bash
# Check the specific errors
agenthub agent validate --verbose

# Common fixes:
# - Add missing required fields to config.json
# - Fix syntax errors in agent code
# - Update requirements.txt
```

#### "Test failed"
```bash
# Check agent code syntax
python my_agent.py

# Test with simpler input
agenthub agent test --input '{}'
```

#### "Publishing failed"
```bash
# Check configuration
agenthub config --show

# Validate first
agenthub agent validate

# Try dry run
agenthub agent publish --dry-run
```

### Debug Mode

Use verbose mode for detailed output:

```bash
agenthub --verbose agent validate
agenthub --verbose agent test
agenthub --verbose agent publish
```

## Advanced Usage

### Custom Agent Types

You can create custom agent types by extending the base templates:

```python
# custom_agent.py
from typing import Dict, Any

class CustomAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your custom logic here
        return {"result": "custom processing"}

def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    agent = CustomAgent(config)
    return agent.process(input_data)
```

### Batch Operations

Process multiple agents:

```bash
# Validate multiple agents
find . -name "config.json" -execdir agenthub agent validate \;

# Test multiple agents
for dir in */; do
    if [ -f "$dir/config.json" ]; then
        echo "Testing $dir"
        (cd "$dir" && agenthub agent test)
    fi
done
```

### CI/CD Integration

Use the CLI in your CI/CD pipeline:

```yaml
# .github/workflows/agent-validation.yml
name: Agent Validation
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install CLI
        run: |
          cd agent-hiring-mvp/agenthub-sdk
          pip install -e .
      - name: Validate agents
        run: |
          agenthub agent validate
          agenthub agent test
```

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the [Agent Creation Guide](AGENT_CREATION_GUIDE.md)
- Run commands with `--verbose` flag for detailed output
- Check the [GitHub Issues](https://github.com/your-org/agenthub/issues) 