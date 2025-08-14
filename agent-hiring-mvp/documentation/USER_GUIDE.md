# 📖 AgentHub User Guide

Complete guide to using AgentHub for AI agent discovery, hiring, and execution.

## 📚 Table of Contents

1. [Understanding AgentHub](#understanding-agenthub)
2. [Getting Started](#getting-started)
3. [Discovering Agents](#discovering-agents)
4. [Hiring Agents](#hiring-agents)
5. [Executing Agents](#executing-agents)
6. [Managing Your Portfolio](#managing-your-portfolio)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## 🎯 Understanding AgentHub

### What is AgentHub?

AgentHub is an AI agent marketplace that connects users with specialized AI capabilities. Think of it as a "job board" for AI agents where you can:

- **Hire agents** for specific tasks
- **Execute tasks** and get results
- **Manage multiple agents** in your portfolio
- **Track usage** and costs

### Key Concepts

| Term | Definition |
|------|------------|
| **Agent** | An AI program that can perform specific tasks |
| **Hiring** | The process of reserving an agent for your use |
| **Execution** | Running a task on a hired agent |
| **Deployment** | A running instance of a hired agent |
| **ACP** | Agent Communication Protocol for standardized communication |

### How It Works

```
1. Discover → 2. Hire → 3. Deploy → 4. Execute → 5. Results
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+ installed
- AgentHub CLI installed
- Platform server running
- Basic understanding of JSON

### First Steps

1. **Install CLI**: `pip install -e ./agenthub-sdk`
2. **Start Platform**: `python -m server.main --dev`
3. **Verify**: `curl http://localhost:8000/health`

## 🔍 Discovering Agents

### Browsing Available Agents

```bash
# List all agents
agenthub agent list

# Get detailed information about a specific agent
agenthub agent info <agent_id>

# Search for agents by category
agenthub agent list --category "data-analysis"

# Filter by tags
agenthub agent list --tags "python,research"
```

### Understanding Agent Information

When you view agent details, you'll see:

- **Basic Info**: Name, description, author
- **Capabilities**: What the agent can do
- **Requirements**: Input format, dependencies
- **Pricing**: Cost per execution or monthly fee
- **Performance**: Success rate, average response time

### Agent Categories

| Category | Description | Example Use Cases |
|----------|-------------|-------------------|
| **Data Analysis** | Process and analyze data | Financial analysis, research data |
| **Content Creation** | Generate text, images, code | Blog posts, documentation, scripts |
| **Research** | Gather and synthesize information | Market research, literature review |
| **Automation** | Automate repetitive tasks | Data entry, report generation |
| **Integration** | Connect different systems | API integration, data migration |

## 💼 Hiring Agents

### The Hiring Process

Hiring an agent reserves it for your use and creates a persistent connection.

```bash
# Hire an agent
agenthub hire agent <agent_id>

# Hire with specific configuration
agenthub hire agent <agent_id> --config '{"setting": "value"}'

# Hire multiple agents
agenthub hire agent <agent_id1> <agent_id2>
```

### Hiring Options

| Option | Description | Example |
|--------|-------------|---------|
| **Basic Hire** | Standard hiring with default settings | `agenthub hire agent 1` |
| **Configured Hire** | Hire with custom configuration | `agenthub hire agent 1 --config '{"model": "gpt-4"}'` |
| **Bulk Hire** | Hire multiple agents at once | `agenthub hire agent 1 2 3` |

### What Happens When You Hire

1. **Resource Allocation**: Platform reserves resources for your agent
2. **Deployment Creation**: A deployment instance is created
3. **Configuration Setup**: Your custom settings are applied
4. **Persistent Link**: You get a permanent communication channel

### Hiring Status

```bash
# Check hiring status
agenthub hired info <hiring_id>

# List all your hirings
agenthub hired list

# View hiring details
agenthub hired details <hiring_id>
```

## ⚡ Executing Agents

### Basic Execution

```bash
# Execute a hired agent
agenthub execute hiring <hiring_id> --input '{"task": "Hello!"}'

# Execute with file input
agenthub execute hiring <hiring_id> --input-file input.json

# Execute with custom timeout
agenthub execute hiring <hiring_id> --input '{"data": "test"}' --timeout 60
```

### Input Formats

#### Simple Text Input
```json
{
  "message": "Hello, agent!",
  "task": "Process this request"
}
```

#### Structured Data Input
```json
{
  "data": {
    "text": "Sample text to analyze",
    "format": "markdown",
    "options": {
      "summarize": true,
      "extract_keywords": true
    }
  }
}
```

#### File Input
```json
{
  "file_path": "/path/to/file.txt",
  "operation": "analyze",
  "parameters": {
    "language": "en",
    "sentiment": true
  }
}
```

### Execution Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | JSON input data | Required |
| `--input-file` | File containing input | None |
| `--timeout` | Execution timeout in seconds | 30 |
| `--async` | Execute asynchronously | False |
| `--wait` | Wait for completion | True |

### Understanding Results

#### Successful Execution
```json
{
  "status": "success",
  "result": {
    "output": "Processed result",
    "metadata": {
      "execution_time": 2.5,
      "tokens_used": 150
    }
  },
  "hiring_id": "hiring_123"
}
```

#### Error Response
```json
{
  "status": "error",
  "error": "Invalid input format",
  "details": "Expected 'data' field in input",
  "hiring_id": "hiring_123"
}
```

## 🗂️ Managing Your Portfolio

### Viewing Your Hirings

```bash
# List all hired agents
agenthub hired list

# Get detailed information
agenthub hired info <hiring_id>

# View execution history
agenthub hired executions <hiring_id>

# Check resource usage
agenthub hired resources <hiring_id>
```

### Managing Deployments

```bash
# Start a deployment
agenthub deploy start <deployment_id>

# Stop a deployment
agenthub deploy stop <deployment_id>

# Restart a deployment
agenthub deploy restart <deployment_id>

# Check deployment status
agenthub deploy status <deployment_id>
```

### Resource Management

```bash
# View resource usage
agenthub resources usage

# Set resource limits
agenthub resources set-limit --memory 512 --cpu 2

# Monitor costs
agenthub billing costs
```

## 🚀 Advanced Features

### Batch Execution

Execute multiple tasks on the same agent:

```bash
# Execute multiple inputs
agenthub execute hiring <hiring_id> \
  --input '{"task": "task1"}' \
  --input '{"task": "task2"}' \
  --input '{"task": "task3"}'

# Execute from file with multiple inputs
agenthub execute hiring <hiring_id> --input-file batch_tasks.json
```

### Asynchronous Execution

For long-running tasks:

```bash
# Execute asynchronously
agenthub execute hiring <hiring_id> \
  --input '{"task": "long_task"}' \
  --async

# Check status later
agenthub execution status <execution_id>

# Get results when ready
agenthub execution result <execution_id>
```

### Agent Chaining

Combine multiple agents for complex workflows:

```bash
# Execute agent 1 and pass result to agent 2
result1=$(agenthub execute hiring <hiring_id_1> --input '{"task": "step1"}')
agenthub execute hiring <hiring_id_2> --input "{\"input\": $result1}"
```

### Custom Configuration

```bash
# Hire with custom settings
agenthub hire agent <agent_id> \
  --config '{
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000
  }'

# Update configuration
agenthub hired configure <hiring_id> \
  --config '{"temperature": 0.5}'
```

## 🔧 Troubleshooting

### Common Issues

#### Agent Not Responding
```bash
# Check hiring status
agenthub hired info <hiring_id>

# Check deployment status
agenthub deploy status <deployment_id>

# Restart deployment
agenthub deploy restart <deployment_id>
```

#### Execution Errors
```bash
# Check execution status
agenthub execution status <execution_id>

# View error details
agenthub execution logs <execution_id>

# Retry execution
agenthub execute hiring <hiring_id> --input '{"task": "retry"}'
```

#### Resource Issues
```bash
# Check resource usage
agenthub resources usage

# View limits
agenthub resources limits

# Increase limits if needed
agenthub resources set-limit --memory 1024
```

### Getting Help

1. **Check logs**: Look for error messages in the console
2. **Verify status**: Use status commands to check system health
3. **Review configuration**: Ensure your settings are correct
4. **Check documentation**: Refer to this guide and API docs

## 💡 Best Practices

### Agent Selection

- **Read descriptions carefully** to understand capabilities
- **Check performance metrics** for reliability
- **Start with simple agents** before complex ones
- **Test with small inputs** before large tasks

### Input Preparation

- **Use consistent formats** for better results
- **Validate your data** before sending
- **Include context** for better agent understanding
- **Use structured JSON** when possible

### Resource Management

- **Monitor usage** regularly
- **Set appropriate limits** for your needs
- **Stop unused deployments** to save resources
- **Plan for scaling** as your needs grow

### Security

- **Don't send sensitive data** unless necessary
- **Use secure connections** for production
- **Monitor access logs** regularly
- **Keep API keys secure**

## 📚 Next Steps

- **[CLI Reference](CLI_REFERENCE.md)** - Complete command documentation
- **[API Reference](API_REFERENCE.md)** - REST API documentation
- **[Examples & Tutorials](EXAMPLES_TUTORIALS.md)** - Practical examples
- **[Agent Creation Guide](AGENT_CREATION_GUIDE.md)** - Building your own agents

---

**Need help? Check the [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) or run `agenthub --help` for command assistance.**

*Happy agent hiring! 🤖✨*
