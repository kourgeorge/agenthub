# AgentHub CLI - Agent Consumption Guide

This guide covers the agent consumption features of the AgentHub CLI, designed for users who want to discover, hire, and execute agents.

## Overview

The AgentHub CLI now provides comprehensive agent consumption capabilities:

- **Marketplace browsing** - Discover available agents
- **Agent hiring** - Hire agents for your use cases
- **Agent execution** - Execute agents with custom input
- **Job management** - Track execution status and results
- **Hired agent management** - Manage your agent subscriptions

## Command Structure

```
agenthub
├── marketplace          # Browse and discover agents
│   ├── search           # Search for agents
│   └── categories       # List categories
├── hire                 # Hire agents
│   └── agent           # Hire a specific agent
├── execute             # Execute hired agents
│   ├── agent           # Execute with JSON input
│   └── file            # Execute with file input
├── jobs                # Manage execution jobs
│   ├── list            # List recent jobs
│   └── status          # Check job status
└── hired               # Manage hired agents
    ├── list            # List hired agents
    └── info            # Get hiring details
```

## Marketplace Commands

### Search for Agents

```bash
# Basic search
agenthub marketplace search

# Search with query
agenthub marketplace search --query "data analysis"

# Filter by category
agenthub marketplace search --category "analytics"

# Filter by pricing model
agenthub marketplace search --pricing "free"

# Combine filters
agenthub marketplace search --query "chat" --category "communication" --limit 5
```

### Browse Categories

```bash
# List all available categories
agenthub marketplace categories
```

**Example Output:**
```
Available categories:
  • analytics
  • communication
  • data-processing
  • general
  • utilities
```

## Agent Hiring

### Hire an Agent

```bash
# Basic hiring
agenthub hire agent 123

# Hire with specific billing cycle
agenthub hire agent 123 --billing-cycle "monthly"

# Hire with configuration
agenthub hire agent 123 --config '{"api_key": "your-key", "timeout": 30}'

# Multi-user hiring
agenthub hire agent 123 --user-id 456 --billing-cycle "per_use"
```

**Options:**
- `--config, -c`: JSON configuration for the agent
- `--billing-cycle, -b`: Billing cycle (per_use, monthly)
- `--user-id, -u`: User ID for multi-user scenarios
- `--base-url`: AgentHub server URL

## Agent Execution

### Execute with JSON Input

```bash
# Basic execution
agenthub execute agent 123 --input '{"message": "Hello, world!"}'

# Execute and wait for completion
agenthub execute agent 123 --input '{"data": [1,2,3]}' --wait

# Execute with configuration
agenthub execute agent 123 \
  --input '{"message": "Process this"}' \
  --config '{"debug": true}' \
  --wait

# Execute with custom timeout
agenthub execute agent 123 \
  --input '{"task": "long_running"}' \
  --wait \
  --timeout 300
```

### Execute with File Input

```bash
# Execute with input from file
agenthub execute file 123 input.json --wait

# Execute file with configuration
agenthub execute file 123 data.json \
  --config '{"format": "csv"}' \
  --wait
```

**Input File Example (input.json):**
```json
{
  "data": [1, 2, 3, 4, 5],
  "operation": "sum",
  "format": "json"
}
```

### Execution Options

- `--input, -i`: JSON input data (required for `agent` command)
- `--config, -c`: JSON configuration for the agent
- `--hiring-id, -h`: Hiring ID if already hired
- `--user-id, -u`: User ID
- `--wait, -w`: Wait for completion (synchronous execution)
- `--timeout, -t`: Timeout in seconds (default: 60)
- `--base-url`: AgentHub server URL

## Job Management

### List Execution Jobs

```bash
# List recent jobs
agenthub jobs list

# List with filters
agenthub jobs list --user-id 123 --limit 20 --status "completed"
```

### Check Job Status

```bash
# Check execution status
agenthub jobs status abc-def-123

# Check with custom server
agenthub jobs status abc-def-123 --base-url "https://staging.agenthub.com"
```

**Example Status Output:**
```
📊 Execution Status:
  ID: abc-def-123
  Status: completed
  Created: 2024-01-15T10:30:00Z
  Updated: 2024-01-15T10:31:00Z

📋 Result:
{
  "result": "Task completed successfully",
  "processing_time": 45.2,
  "items_processed": 1000
}
```

## Hired Agent Management

### List Hired Agents

```bash
# List your hired agents
agenthub hired list

# List for specific user
agenthub hired list --user-id 123
```

**Example Output:**
```
Found 3 hired agents:

🤖 Data Processor (Hiring ID: 456)
   Agent ID: 123 | Category: analytics
   Hired: 2024-01-10T09:00:00Z | Status: active
   Billing: per_use

🤖 Chat Assistant (Hiring ID: 789)
   Agent ID: 124 | Category: communication
   Hired: 2024-01-12T14:30:00Z | Status: active
   Billing: monthly
```

### Get Hiring Details

```bash
# Get detailed hiring information
agenthub hired info 456
```

## Usage Examples

### Complete Workflow Example

```bash
# 1. Discover agents
agenthub marketplace search --query "data analysis" --limit 5

# 2. Get agent details
agenthub agent info 123

# 3. Hire the agent
agenthub hire agent 123 --billing-cycle "per_use"

# 4. Execute the agent
agenthub execute agent 123 \
  --input '{"data": [1,2,3,4,5], "operation": "average"}' \
  --wait

# 5. Check execution history
agenthub jobs list --limit 5
```

### Data Processing Workflow

```bash
# Find data processing agents
agenthub marketplace search --category "data-processing"

# Hire a data processor
agenthub hire agent 125 --config '{"output_format": "csv"}'

# Process a data file
agenthub execute file 125 large_dataset.json \
  --config '{"batch_size": 1000}' \
  --wait \
  --timeout 600

# Check results
agenthub jobs status <execution-id>
```

### Chat Agent Workflow

```bash
# Find chat agents
agenthub marketplace search --category "communication" --pricing "free"

# Hire a chat agent
agenthub hire agent 130

# Start conversation
agenthub execute agent 130 \
  --input '{"message": "Hello, how can you help me?"}' \
  --wait

# Continue conversation with history
agenthub execute agent 130 \
  --input '{
    "message": "What services do you offer?",
    "conversation_history": [
      {"role": "user", "content": "Hello, how can you help me?"},
      {"role": "assistant", "content": "Hello! I can help with various tasks..."}
    ]
  }' \
  --wait
```

## Configuration and Authentication

### Set Default Configuration

```bash
# Configure default settings
agenthub config --base-url "https://your-agenthub.com"
agenthub config --author "Your Name"
agenthub config --email "your@email.com"

# View current config
agenthub config --show
```

### Using Different Servers

```bash
# Use staging environment
agenthub marketplace search --base-url "https://staging.agenthub.com"

# Use local development server
agenthub execute agent 123 \
  --input '{"test": true}' \
  --base-url "http://localhost:8002"
```

## Error Handling and Troubleshooting

### Common Issues

#### Agent Not Found
```bash
$ agenthub agent info 999
✗ Error getting agent info: Agent not found
```

#### Execution Timeout
```bash
$ agenthub execute agent 123 --input '{"task": "heavy"}' --timeout 10
✗ Error executing agent: Execution timeout after 10 seconds
```

#### Invalid Input Format
```bash
$ agenthub execute agent 123 --input 'invalid json'
✗ Error executing agent: Invalid JSON input
```

### Best Practices

1. **Always validate JSON input:**
   ```bash
   echo '{"test": "data"}' | jq . # Validate JSON
   ```

2. **Use appropriate timeouts:**
   ```bash
   # For quick tasks
   agenthub execute agent 123 --input '{"quick": true}' --timeout 30
   
   # For heavy processing
   agenthub execute agent 123 --input '{"heavy": true}' --timeout 600
   ```

3. **Handle large datasets with files:**
   ```bash
   # Instead of huge JSON strings, use files
   agenthub execute file 123 large_data.json --wait
   ```

4. **Check agent details before hiring:**
   ```bash
   agenthub agent info 123  # Check pricing, requirements, etc.
   agenthub hire agent 123  # Then hire
   ```

## Advanced Features

### Batch Processing

```bash
# Process multiple files
for file in data/*.json; do
  echo "Processing $file"
  agenthub execute file 123 "$file" --wait
done
```

### Scripting Integration

```bash
#!/bin/bash
# Auto-hire and execute script

AGENT_ID=123
INPUT_DATA='{"batch": true, "items": 1000}'

echo "Hiring agent $AGENT_ID..."
HIRE_RESULT=$(agenthub hire agent $AGENT_ID --billing-cycle per_use)

if [[ $? -eq 0 ]]; then
  echo "Executing agent..."
  agenthub execute agent $AGENT_ID --input "$INPUT_DATA" --wait
else
  echo "Failed to hire agent"
  exit 1
fi
```

### JSON Processing with jq

```bash
# Extract execution results
agenthub execute agent 123 --input '{"data": [1,2,3]}' --wait | jq '.result'

# Process multiple results
agenthub jobs list | jq '.jobs[] | select(.status == "completed") | .result'
```

## Integration with Other Tools

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Execute Agent
  run: |
    agenthub execute agent 123 \
      --input '{"repository": "${{ github.repository }}"}' \
      --wait \
      --timeout 300
```

### Monitoring and Alerting

```bash
# Check for failed executions
agenthub jobs list --status failed | jq '.jobs | length'

# Alert on execution failures
if [ $(agenthub jobs list --status failed | jq '.jobs | length') -gt 0 ]; then
  echo "ALERT: Failed executions detected"
  # Send notification
fi
```

## Summary

The AgentHub CLI consumption features provide a complete toolkit for discovering, hiring, and executing agents:

✅ **Marketplace Discovery** - Find the right agents for your needs  
✅ **Flexible Hiring** - Support for multiple billing models  
✅ **Versatile Execution** - JSON input, file input, sync/async modes  
✅ **Job Management** - Track execution status and results  
✅ **Subscription Management** - Manage your hired agents  
✅ **Integration Ready** - Perfect for scripts, CI/CD, and automation  

The CLI bridges the gap between the AgentHub platform and everyday workflows, making AI agents as easy to use as any other command-line tool. 