# 🖥️ AgentHub CLI Reference

Complete reference for the AgentHub command-line interface.

## 📚 Table of Contents

1. [Command Overview](#command-overview)
2. [Global Options](#global-options)
3. [Agent Commands](#agent-commands)
4. [Hiring Commands](#hiring-commands)
5. [Execution Commands](#execution-commands)
6. [Deployment Commands](#deployment-commands)
7. [Resource Commands](#resource-commands)
8. [Billing Commands](#billing-commands)
9. [Utility Commands](#utility-commands)
10. [Examples](#examples)

## 🎯 Command Overview

The AgentHub CLI provides a comprehensive interface for managing AI agents, hirings, and executions.

### Basic Syntax

```bash
agenthub <command> <subcommand> [options] [arguments]
```

### Command Categories

| Category | Commands | Description |
|----------|----------|-------------|
| **Agent Management** | `agent` | Create, validate, test, and publish agents |
| **Hiring** | `hire`, `hired` | Hire agents and manage hirings |
| **Execution** | `execute`, `execution` | Execute tasks on hired agents |
| **Deployment** | `deploy` | Manage agent deployments |
| **Resources** | `resources` | Monitor and manage resource usage |
| **Billing** | `billing` | Track costs and manage billing |

## 🌐 Global Options

These options are available for all commands:

| Option | Description | Example |
|--------|-------------|---------|
| `--help`, `-h` | Show help for command | `agenthub --help` |
| `--version` | Show version information | `agenthub --version` |
| `--verbose`, `-v` | Enable verbose output | `agenthub agent list --verbose` |
| `--quiet`, `-q` | Suppress output | `agenthub agent list --quiet` |
| `--config` | Configuration file path | `agenthub --config config.yaml` |
| `--api-url` | API server URL | `agenthub --api-url https://api.agenthub.com` |

## 🤖 Agent Commands

### `agenthub agent`

Manage AI agents on the platform.

#### `agenthub agent list`

List available agents.

```bash
# List all agents
agenthub agent list

# List with details
agenthub agent list --detailed

# Filter by category
agenthub agent list --category "data-analysis"

# Filter by tags
agenthub agent list --tags "python,research"

# Search by name
agenthub agent list --search "research"

# Limit results
agenthub agent list --limit 10

# Sort by field
agenthub agent list --sort-by "name" --sort-order "asc"
```

**Options:**
- `--detailed`: Show detailed information
- `--category <category>`: Filter by category
- `--tags <tags>`: Filter by comma-separated tags
- `--search <query>`: Search by name or description
- `--limit <number>`: Limit number of results
- `--sort-by <field>`: Sort by field (name, category, rating)
- `--sort-order <order>`: Sort order (asc, desc)

#### `agenthub agent info <agent_id>`

Get detailed information about a specific agent.

```bash
# Get agent information
agenthub agent info 1

# Show with examples
agenthub agent info 1 --examples

# Show configuration options
agenthub agent info 1 --config-options
```

**Options:**
- `--examples`: Show usage examples
- `--config-options`: Show configuration options
- `--performance`: Show performance metrics

#### `agenthub agent init`

Initialize a new agent project.

```bash
# Initialize in current directory
agenthub agent init

# Initialize with template
agenthub agent init --template "academic_research"

# Initialize with custom name
agenthub agent init --name "My Custom Agent"

# Initialize with specific path
agenthub agent init --path "./my_agent"
```

**Options:**
- `--template <template>`: Use specific template
- `--name <name>`: Set agent name
- `--path <path>`: Set project path
- `--force`: Overwrite existing files

#### `agenthub agent validate`

Validate agent configuration and code.

```bash
# Validate current agent
agenthub agent validate

# Validate specific path
agenthub agent validate --path "./my_agent"

# Validate with detailed output
agenthub agent validate --detailed

# Validate and fix issues
agenthub agent validate --fix
```

**Options:**
- `--path <path>`: Path to agent directory
- `--detailed`: Show detailed validation results
- `--fix`: Attempt to fix validation issues
- `--strict`: Use strict validation rules

#### `agenthub agent test`

Test agent locally.

```bash
# Test with default input
agenthub agent test

# Test with custom input
agenthub agent test --input '{"test": "data"}'

# Test with input file
agenthub agent test --input-file test_input.json

# Test with timeout
agenthub agent test --timeout 60

# Test multiple inputs
agenthub agent test --input '{"test1": "data1"}' --input '{"test2": "data2"}'
```

**Options:**
- `--input <json>`: Test input data
- `--input-file <file>`: File containing test input
- `--timeout <seconds>`: Test timeout
- `--verbose`: Show detailed test output

#### `agenthub agent publish`

Publish agent to the platform.

```bash
# Publish current agent
agenthub agent publish

# Publish with description
agenthub agent publish --description "My awesome agent"

# Publish with tags
agenthub agent publish --tags "python,research,ai"

# Publish with category
agenthub agent publish --category "data-analysis"

# Publish with pricing
agenthub agent publish --pricing "per-use:0.01"
```

**Options:**
- `--description <text>`: Agent description
- `--tags <tags>`: Comma-separated tags
- `--category <category>`: Agent category
- `--pricing <model>`: Pricing model
- `--public`: Make agent publicly available
- `--force`: Overwrite existing agent

## 💼 Hiring Commands

### `agenthub hire`

Hire agents for your use.

#### `agenthub hire agent <agent_id>`

Hire a specific agent.

```bash
# Basic hire
agenthub hire agent 1

# Hire with configuration
agenthub hire agent 1 --config '{"model": "gpt-4"}'

# Hire with custom settings
agenthub hire agent 1 --config '{"temperature": 0.7, "max_tokens": 1000}'

# Hire multiple agents
agenthub hire agent 1 2 3

# Hire with name
agenthub hire agent 1 --name "My Research Agent"
```

**Options:**
- `--config <json>`: Agent configuration
- `--name <name>`: Custom hiring name
- `--description <text>`: Hiring description
- `--tags <tags>`: Custom tags

### `agenthub hired`

Manage your hired agents.

#### `agenthub hired list`

List all your hirings.

```bash
# List all hirings
agenthub hired list

# List with details
agenthub hired list --detailed

# Filter by status
agenthub hired list --status "active"

# Filter by agent category
agenthub hired list --category "research"

# Sort by field
agenthub hired list --sort-by "created_at" --sort-order "desc"
```

**Options:**
- `--detailed`: Show detailed information
- `--status <status>`: Filter by status (active, suspended, stopped)
- `--category <category>`: Filter by agent category
- `--sort-by <field>`: Sort by field
- `--sort-order <order>`: Sort order

#### `agenthub hired info <hiring_id>`

Get information about a specific hiring.

```bash
# Get hiring information
agenthub hired info hiring_123

# Show with executions
agenthub hired info hiring_123 --executions

# Show with resources
agenthub hired info hiring_123 --resources
```

**Options:**
- `--executions`: Show execution history
- `--resources`: Show resource usage
- `--config`: Show current configuration

#### `agenthub hired configure <hiring_id>`

Update hiring configuration.

```bash
# Update configuration
agenthub hired configure hiring_123 --config '{"temperature": 0.5}'

# Update name
agenthub hired configure hiring_123 --name "Updated Name"

# Update description
agenthub hired configure hiring_123 --description "New description"
```

**Options:**
- `--config <json>`: New configuration
- `--name <name>`: New hiring name
- `--description <text>`: New description

#### `agenthub hired suspend <hiring_id>`

Suspend a hiring (keeps resources but stops execution).

```bash
# Suspend hiring
agenthub hired suspend hiring_123

# Suspend with reason
agenthub hired suspend hiring_123 --reason "Temporary pause"
```

**Options:**
- `--reason <text>`: Reason for suspension

#### `agenthub hired resume <hiring_id>`

Resume a suspended hiring.

```bash
# Resume hiring
agenthub hired resume hiring_123
```

#### `agenthub hired stop <hiring_id>`

Stop a hiring and free all resources.

```bash
# Stop hiring
agenthub hired stop hiring_123

# Stop with reason
agenthub hired stop hiring_123 --reason "No longer needed"
```

**Options:**
- `--reason <text>`: Reason for stopping

## ⚡ Execution Commands

### `agenthub execute`

Execute tasks on hired agents.

#### `agenthub execute hiring <hiring_id>`

Execute a task on a hired agent.

```bash
# Basic execution
agenthub execute hiring hiring_123 --input '{"task": "Hello!"}'

# Execute with file input
agenthub execute hiring hiring_123 --input-file input.json

# Execute with timeout
agenthub execute hiring hiring_123 --input '{"data": "test"}' --timeout 60

# Execute asynchronously
agenthub execute hiring hiring_123 --input '{"task": "long_task"}' --async

# Execute multiple inputs
agenthub execute hiring hiring_123 \
  --input '{"task": "task1"}' \
  --input '{"task": "task2"}'
```

**Options:**
- `--input <json>`: Input data (required)
- `--input-file <file>`: File containing input data
- `--timeout <seconds>`: Execution timeout (default: 30)
- `--async`: Execute asynchronously
- `--wait`: Wait for completion (default: true)
- `--format <format>`: Output format (json, text, table)

#### `agenthub execute agent <agent_id>`

Execute a task directly on an agent (bypasses hiring).

```bash
# Direct execution
agenthub execute agent 1 --input '{"task": "Quick test"}'

# Execute with configuration
agenthub execute agent 1 \
  --input '{"task": "test"}' \
  --config '{"model": "gpt-4"}'
```

**Options:**
- `--input <json>`: Input data (required)
- `--config <json>`: Agent configuration
- `--timeout <seconds>`: Execution timeout

### `agenthub execution`

Manage executions.

#### `agenthub execution status <execution_id>`

Check execution status.

```bash
# Check status
agenthub execution status exec_123

# Show with details
agenthub execution status exec_123 --detailed
```

**Options:**
- `--detailed`: Show detailed status information

#### `agenthub execution result <execution_id>`

Get execution result.

```bash
# Get result
agenthub execution result exec_123

# Get with metadata
agenthub execution result exec_123 --metadata
```

**Options:**
- `--metadata`: Include execution metadata

#### `agenthub execution logs <execution_id>`

View execution logs.

```bash
# View logs
agenthub execution logs exec_123

# Follow logs in real-time
agenthub execution logs exec_123 --follow

# Show last N lines
agenthub execution logs exec_123 --tail 100
```

**Options:**
- `--follow`: Follow logs in real-time
- `--tail <lines>`: Show last N lines
- `--level <level>`: Log level (debug, info, warn, error)

## 🚀 Deployment Commands

### `agenthub deploy`

Manage agent deployments.

#### `agenthub deploy create <hiring_id>`

Create a deployment for a hired agent.

```bash
# Create deployment
agenthub deploy create hiring_123

# Create with configuration
agenthub deploy create hiring_123 --config '{"replicas": 2}'
```

**Options:**
- `--config <json>`: Deployment configuration

#### `agenthub deploy start <deployment_id>`

Start a deployment.

```bash
# Start deployment
agenthub deploy start deploy_123
```

#### `agenthub deploy stop <deployment_id>`

Stop a deployment.

```bash
# Stop deployment
agenthub deploy stop deploy_123
```

#### `agenthub deploy restart <deployment_id>`

Restart a deployment.

```bash
# Restart deployment
agenthub deploy restart deploy_123
```

#### `agenthub deploy status <deployment_id>`

Check deployment status.

```bash
# Check status
agenthub deploy status deploy_123

# Show with details
agenthub deploy status deploy_123 --detailed
```

**Options:**
- `--detailed`: Show detailed status information

#### `agenthub deploy list`

List all deployments.

```bash
# List deployments
agenthub deploy list

# List with details
agenthub deploy list --detailed

# Filter by status
agenthub deploy list --status "running"
```

**Options:**
- `--detailed`: Show detailed information
- `--status <status>`: Filter by status

## 📊 Resource Commands

### `agenthub resources`

Manage resource usage and limits.

#### `agenthub resources usage`

Show current resource usage.

```bash
# Show usage
agenthub resources usage

# Show with details
agenthub resources usage --detailed

# Show by hiring
agenthub resources usage --by-hiring
```

**Options:**
- `--detailed`: Show detailed usage information
- `--by-hiring`: Group usage by hiring

#### `agenthub resources limits`

Show current resource limits.

```bash
# Show limits
agenthub resources limits
```

#### `agenthub resources set-limit`

Set resource limits.

```bash
# Set memory limit
agenthub resources set-limit --memory 512

# Set CPU limit
agenthub resources set-limit --cpu 2

# Set multiple limits
agenthub resources set-limit --memory 1024 --cpu 4
```

**Options:**
- `--memory <mb>`: Memory limit in MB
- `--cpu <cores>`: CPU limit in cores
- `--timeout <seconds>`: Execution timeout

## 💰 Billing Commands

### `agenthub billing`

Manage billing and costs.

#### `agenthub billing costs`

Show cost information.

```bash
# Show costs
agenthub billing costs

# Show by period
agenthub billing costs --period "month"

# Show by hiring
agenthub billing costs --by-hiring
```

**Options:**
- `--period <period>`: Time period (day, week, month, year)
- `--by-hiring`: Group costs by hiring

#### `agenthub billing history`

Show billing history.

```bash
# Show history
agenthub billing history

# Show with details
agenthub billing history --detailed
```

**Options:**
- `--detailed`: Show detailed billing information

## 🛠️ Utility Commands

### `agenthub version`

Show version information.

```bash
agenthub version
```

### `agenthub status`

Show system status.

```bash
# Show status
agenthub status

# Show with details
agenthub status --detailed
```

**Options:**
- `--detailed`: Show detailed status information

### `agenthub config`

Manage configuration.

```bash
# Show configuration
agenthub config

# Set configuration value
agenthub config set api_url https://api.agenthub.com

# Get configuration value
agenthub config get api_url
```

## 📝 Examples

### Complete Workflow Example

```bash
# 1. Browse available agents
agenthub agent list --category "research"

# 2. Get agent details
agenthub agent info 1

# 3. Hire the agent
agenthub hire agent 1 --config '{"model": "gpt-4"}'

# 4. Check hiring status
agenthub hired list

# 5. Execute a task
agenthub execute hiring hiring_123 --input '{"task": "Research AI trends"}'

# 6. Check execution status
agenthub execution status exec_456

# 7. Get results
agenthub execution result exec_456
```

### Batch Processing Example

```bash
# Hire multiple agents
agenthub hire agent 1 2 3

# Execute batch tasks
agenthub execute hiring hiring_123 \
  --input '{"task": "Process data 1"}' \
  --input '{"task": "Process data 2"}' \
  --input '{"task": "Process data 3"}'
```

### Configuration Management Example

```bash
# Set global configuration
agenthub config set api_url https://api.agenthub.com
agenthub config set timeout 60

# Hire with custom config
agenthub hire agent 1 --config '{
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 1000
}'

# Update hiring configuration
agenthub hired configure hiring_123 --config '{"temperature": 0.5}'
```

## 🔧 Getting Help

### Command Help

```bash
# General help
agenthub --help

# Command help
agenthub agent --help

# Subcommand help
agenthub agent list --help
```

### Error Handling

The CLI provides helpful error messages and suggestions:

```bash
# Invalid command
agenthub invalid_command
# Error: No such command 'invalid_command'. Try 'agenthub --help'

# Missing required argument
agenthub agent info
# Error: Missing argument 'AGENT_ID'. Try 'agenthub agent info --help'
```

### Verbose Output

Use `--verbose` for detailed information:

```bash
agenthub agent list --verbose
```

---

**For more information, see the [User Guide](USER_GUIDE.md) or run `agenthub --help` for command assistance.**

*Happy CLI usage! 🖥️✨*
