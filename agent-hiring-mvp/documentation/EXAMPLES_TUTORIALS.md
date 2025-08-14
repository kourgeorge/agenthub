# 📚 AgentHub Examples & Tutorials

Practical examples and step-by-step tutorials for common AgentHub use cases.

## 📚 Table of Contents

1. [Quick Start Tutorial](#quick-start-tutorial)
2. [Agent Discovery Examples](#agent-discovery-examples)
3. [Hiring & Deployment Examples](#hiring--deployment-examples)
4. [Execution Examples](#execution-examples)
5. [Workflow Examples](#workflow-examples)
6. [Integration Examples](#integration-examples)
7. [Troubleshooting Examples](#troubleshooting-examples)

## 🚀 Quick Start Tutorial

### Complete First-Time User Experience

This tutorial walks you through your first complete workflow with AgentHub.

#### Step 1: Setup and Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd agent-hiring-mvp

# 2. Install the CLI
pip install -e ./agenthub-sdk

# 3. Start the platform
python -m server.main --dev

# 4. Verify installation
agenthub --version
```

#### Step 2: Discover Your First Agent

```bash
# 1. List available agents
agenthub agent list

# 2. Get details about a specific agent
agenthub agent info 1

# 3. Search for agents by category
agenthub agent list --category "research"
```

#### Step 3: Hire and Execute

```bash
# 1. Hire an agent
agenthub hire agent 1

# 2. Check your hiring
agenthub hired list

# 3. Execute a simple task
agenthub execute hiring hiring_123 --input '{"task": "Hello, agent!"}'

# 4. View results
agenthub execution result exec_456
```

🎉 **Congratulations! You've completed your first AgentHub workflow!**

## 🔍 Agent Discovery Examples

### Example 1: Finding Research Agents

```bash
# Find all research-related agents
agenthub agent list --category "research"

# Search for agents with specific capabilities
agenthub agent list --tags "academic,literature-review"

# Get detailed information about a research agent
agenthub agent info 1 --examples --config-options
```

**Expected Output:**
```
ID  Name                    Category    Tags                    Rating
1   Academic Research      research    academic,literature     4.8
2   Market Research        research    business,analysis      4.6
3   Scientific Research    research    science,data           4.9
```

### Example 2: Finding Data Analysis Agents

```bash
# Find data analysis agents
agenthub agent list --category "data-analysis"

# Filter by specific data types
agenthub agent list --tags "csv,json,excel"

# Search for agents by name
agenthub agent list --search "financial"
```

### Example 3: Finding Content Creation Agents

```bash
# Find content creation agents
agenthub agent list --category "content-creation"

# Filter by content type
agenthub agent list --tags "blog,article,marketing"

# Sort by rating
agenthub agent list --category "content-creation" --sort-by "rating" --sort-order "desc"
```

## 💼 Hiring & Deployment Examples

### Example 1: Basic Agent Hiring

```bash
# Hire a single agent
agenthub hire agent 1

# Hire with custom name
agenthub hire agent 1 --name "My Research Assistant"

# Hire with configuration
agenthub hire agent 1 --config '{"model": "gpt-4", "temperature": 0.7}'
```

**Expected Output:**
```
✅ Successfully hired agent "Academic Research Agent"
Hiring ID: hiring_abc123
Status: active
Deployment: deploy_xyz789
```

### Example 2: Multiple Agent Hiring

```bash
# Hire multiple agents at once
agenthub hire agent 1 2 3

# Hire with different configurations
agenthub hire agent 1 --config '{"model": "gpt-4"}' \
       --name "Research Agent"
agenthub hire agent 2 --config '{"model": "gpt-3.5-turbo"}' \
       --name "Analysis Agent"
```

### Example 3: Deployment Management

```bash
# Create deployment for hired agent
agenthub deploy create hiring_abc123

# Check deployment status
agenthub deploy status deploy_xyz789

# Start deployment
agenthub deploy start deploy_xyz789

# Stop deployment when not needed
agenthub deploy stop deploy_xyz789
```

## ⚡ Execution Examples

### Example 1: Simple Text Processing

```bash
# Execute with simple text input
agenthub execute hiring hiring_abc123 \
  --input '{"text": "Hello, how are you today?", "task": "greeting"}'

# Execute with structured input
agenthub execute hiring hiring_abc123 \
  --input '{
    "data": {
      "text": "Sample text for analysis",
      "format": "plain",
      "options": {
        "sentiment": true,
        "keywords": true,
        "summary": true
      }
    }
  }'
```

**Expected Output:**
```json
{
  "status": "success",
  "result": {
    "sentiment": "positive",
    "keywords": ["sample", "text", "analysis"],
    "summary": "A sample text provided for analysis purposes",
    "confidence": 0.95
  },
  "execution_id": "exec_123",
  "hiring_id": "hiring_abc123"
}
```

### Example 2: File Processing

```bash
# Create input file
cat > input.json << EOF
{
  "file_path": "/path/to/document.txt",
  "operation": "analyze",
  "parameters": {
    "language": "en",
    "extract_entities": true,
    "summarize": true
  }
}
EOF

# Execute with file input
agenthub execute hiring hiring_abc123 --input-file input.json
```

### Example 3: Batch Processing

```bash
# Execute multiple tasks
agenthub execute hiring hiring_abc123 \
  --input '{"task": "Analyze text 1", "text": "First sample text"}' \
  --input '{"task": "Analyze text 2", "text": "Second sample text"}' \
  --input '{"task": "Analyze text 3", "text": "Third sample text"}'
```

### Example 4: Asynchronous Execution

```bash
# Execute long-running task asynchronously
agenthub execute hiring hiring_abc123 \
  --input '{"task": "Complex analysis", "data": "large_dataset"}' \
  --async

# Check status later
agenthub execution status exec_456

# Get results when ready
agenthub execution result exec_456
```

## 🔄 Workflow Examples

### Example 1: Research Workflow

This example shows how to chain multiple agents for a research project.

```bash
# Step 1: Hire research agent
agenthub hire agent 1 --name "Research Agent" \
  --config '{"model": "gpt-4", "max_tokens": 2000}'

# Step 2: Hire analysis agent
agenthub hire agent 2 --name "Analysis Agent" \
  --config '{"model": "gpt-4", "temperature": 0.3}'

# Step 3: Execute research
research_result=$(agenthub execute hiring hiring_research \
  --input '{"topic": "AI trends 2024", "depth": "comprehensive"}')

# Step 4: Analyze research results
analysis_result=$(agenthub execute hiring hiring_analysis \
  --input "{\"research_data\": $research_result, \"analysis_type\": \"trend_analysis\"}")

# Step 5: View final results
echo "Research Results: $research_result"
echo "Analysis Results: $analysis_result"
```

### Example 2: Content Creation Workflow

```bash
# Step 1: Hire content research agent
agenthub hire agent 3 --name "Content Research" \
  --config '{"model": "gpt-4", "max_tokens": 1500}'

# Step 2: Hire content writing agent
agenthub hire agent 4 --name "Content Writer" \
  --config '{"model": "gpt-4", "temperature": 0.8}'

# Step 3: Research content topic
research_data=$(agenthub execute hiring hiring_research \
  --input '{"topic": "Machine Learning Basics", "audience": "beginners"}')

# Step 4: Write content based on research
content=$(agenthub execute hiring hiring_writer \
  --input "{\"topic\": \"Machine Learning Basics\", \"research\": $research_data, \"format\": \"blog_post\"}")

# Step 5: Save results
echo "$content" > ml_basics_blog_post.md
```

### Example 3: Data Processing Pipeline

```bash
# Step 1: Hire data collection agent
agenthub hire agent 5 --name "Data Collector" \
  --config '{"model": "gpt-4", "max_tokens": 1000}'

# Step 2: Hire data processor agent
agenthub hire agent 6 --name "Data Processor" \
  --config '{"model": "gpt-4", "temperature": 0.1}'

# Step 3: Collect data
raw_data=$(agenthub execute hiring hiring_collector \
  --input '{"source": "api", "endpoint": "financial_data", "period": "last_30_days"}')

# Step 4: Process data
processed_data=$(agenthub execute hiring hiring_processor \
  --input "{\"raw_data\": $raw_data, \"operations\": [\"clean\", \"normalize\", \"aggregate\"]}")

# Step 5: Export results
echo "$processed_data" > processed_financial_data.json
```

## 🔌 Integration Examples

### Example 1: Python Script Integration

```python
#!/usr/bin/env python3
import subprocess
import json
import sys

def execute_agent(hiring_id, input_data):
    """Execute an agent using the CLI."""
    try:
        # Prepare input as JSON string
        input_json = json.dumps(input_data)
        
        # Execute command
        result = subprocess.run([
            'agenthub', 'execute', 'hiring', hiring_id,
            '--input', input_json
        ], capture_output=True, text=True, check=True)
        
        # Parse result
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing agent: {e}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing result: {e}")
        return None

def main():
    # Example usage
    hiring_id = "hiring_abc123"
    
    # Execute agent
    result = execute_agent(hiring_id, {
        "task": "Analyze sentiment",
        "text": "I love this product! It's amazing."
    })
    
    if result:
        print(f"Execution successful: {result}")
    else:
        print("Execution failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Example 2: Shell Script Integration

```bash
#!/bin/bash

# Configuration
HIRING_ID="hiring_abc123"
AGENT_ID="1"

# Function to execute agent
execute_agent() {
    local input="$1"
    local result
    
    result=$(agenthub execute hiring "$HIRING_ID" --input "$input" --format json)
    
    if [ $? -eq 0 ]; then
        echo "$result"
    else
        echo "Error executing agent" >&2
        return 1
    fi
}

# Function to hire agent if not already hired
ensure_agent_hired() {
    if ! agenthub hired list | grep -q "$HIRING_ID"; then
        echo "Hiring agent $AGENT_ID..."
        agenthub hire agent "$AGENT_ID" --name "My Agent"
    fi
}

# Main execution
main() {
    # Ensure agent is hired
    ensure_agent_hired
    
    # Execute tasks
    echo "Executing task 1..."
    result1=$(execute_agent '{"task": "Task 1", "data": "sample1"}')
    echo "Result 1: $result1"
    
    echo "Executing task 2..."
    result2=$(execute_agent '{"task": "Task 2", "data": "sample2"}')
    echo "Result 2: $result2"
}

# Run main function
main "$@"
```

### Example 3: API Integration

```python
#!/usr/bin/env python3
import requests
import json
import time

class AgentHubAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def hire_agent(self, agent_id, config=None):
        """Hire an agent via API."""
        url = f"{self.base_url}/api/hiring/hire/{agent_id}"
        data = {"config": config} if config else {}
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def execute_hiring(self, hiring_id, input_data):
        """Execute a hired agent via API."""
        url = f"{self.base_url}/api/execution/execute"
        data = {
            "hiring_id": hiring_id,
            "input": input_data
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_execution_status(self, execution_id):
        """Get execution status via API."""
        url = f"{self.base_url}/api/execution/{execution_id}/status"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

def main():
    # Initialize API client
    client = AgentHubAPI()
    
    try:
        # Hire an agent
        print("Hiring agent...")
        hiring_result = client.hire_agent(1, {"model": "gpt-4"})
        hiring_id = hiring_result["hiring_id"]
        print(f"Hired agent with ID: {hiring_id}")
        
        # Execute task
        print("Executing task...")
        execution_result = client.execute_hiring(hiring_id, {
            "task": "Hello, agent!",
            "data": "test input"
        })
        execution_id = execution_result["execution_id"]
        print(f"Execution started with ID: {execution_id}")
        
        # Wait for completion and get results
        print("Waiting for completion...")
        while True:
            status = client.get_execution_status(execution_id)
            if status["status"] in ["completed", "failed"]:
                break
            time.sleep(1)
        
        print(f"Execution completed with status: {status['status']}")
        if status["status"] == "completed":
            print(f"Result: {status.get('result', 'No result')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

## 🔧 Troubleshooting Examples

### Example 1: Agent Not Responding

```bash
# Check hiring status
agenthub hired info hiring_abc123

# Check deployment status
agenthub deploy status deploy_xyz789

# Restart deployment if needed
agenthub deploy restart deploy_xyz789

# Check execution logs
agenthub execution logs exec_123 --tail 50
```

### Example 2: Execution Errors

```bash
# Check execution status
agenthub execution status exec_123

# View detailed error logs
agenthub execution logs exec_123 --level error

# Retry with corrected input
agenthub execute hiring hiring_abc123 \
  --input '{"task": "corrected task", "data": "valid data"}'
```

### Example 3: Resource Issues

```bash
# Check resource usage
agenthub resources usage --detailed

# Check current limits
agenthub resources limits

# Increase memory limit if needed
agenthub resources set-limit --memory 1024

# Stop unused deployments
agenthub deploy list --status "running"
agenthub deploy stop deploy_unused_123
```

## 📝 Best Practices

### 1. Input Validation

```bash
# Good: Structured, clear input
agenthub execute hiring hiring_123 \
  --input '{
    "task": "analyze_sentiment",
    "data": {
      "text": "Sample text for analysis",
      "language": "en"
    },
    "options": {
      "detailed": true,
      "confidence_threshold": 0.8
    }
  }'

# Bad: Unclear, unstructured input
agenthub execute hiring hiring_123 \
  --input '{"text": "analyze this"}'
```

### 2. Error Handling

```bash
# Always check execution status
result=$(agenthub execute hiring hiring_123 --input '{"task": "test"}')
execution_id=$(echo "$result" | jq -r '.execution_id')

# Wait for completion
while true; do
    status=$(agenthub execution status "$execution_id")
    if [ "$(echo "$status" | jq -r '.status')" = "completed" ]; then
        break
    elif [ "$(echo "$status" | jq -r '.status')" = "failed" ]; then
        echo "Execution failed"
        exit 1
    fi
    sleep 1
done
```

### 3. Resource Management

```bash
# Set appropriate limits
agenthub resources set-limit --memory 512 --cpu 1

# Monitor usage regularly
agenthub resources usage --by-hiring

# Clean up unused resources
agenthub hired list --status "stopped" | xargs -I {} agenthub hired stop {}
```

---

**Ready to build amazing workflows? Check out the [User Guide](USER_GUIDE.md) for more detailed information!**

*Happy building! 🚀✨*
