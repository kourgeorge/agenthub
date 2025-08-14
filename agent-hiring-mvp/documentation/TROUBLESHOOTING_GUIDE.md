# 🔧 AgentHub Troubleshooting Guide

Comprehensive guide to diagnosing and resolving common issues with AgentHub.

## 📚 Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Installation Issues](#installation-issues)
3. [Platform Startup Issues](#platform-startup-issues)
4. [CLI Issues](#cli-issues)
5. [Agent Hiring Issues](#agent-hiring-issues)
6. [Execution Issues](#execution-issues)
7. [Deployment Issues](#deployment-issues)
8. [Resource Issues](#resource-issues)
9. [API Issues](#api-issues)
10. [Performance Issues](#performance-issues)
11. [Getting Help](#getting-help)

## 🔍 Quick Diagnosis

### System Health Check

Run this command to quickly check your system status:

```bash
# Check system health
agenthub status

# Check platform health
curl http://localhost:8000/health

# Check CLI version
agenthub --version
```

### Common Symptoms & Solutions

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| **CLI not found** | CLI not installed | `pip install -e ./agenthub-sdk` |
| **Connection refused** | Platform not running | `python -m server.main --dev` |
| **Agent not responding** | Hiring expired/stopped | `agenthub hired info <id>` |
| **Execution failed** | Invalid input format | Check input JSON structure |
| **Resource limit exceeded** | Memory/CPU limits too low | `agenthub resources set-limit --memory 1024` |

## 🚀 Installation Issues

### Issue: CLI Command Not Found

**Symptoms:**
```bash
$ agenthub --version
-bash: agenthub: command not found
```

**Causes:**
- CLI not installed
- Python path issues
- Virtual environment not activated

**Solutions:**

#### Solution 1: Install CLI
```bash
# Navigate to project directory
cd agent-hiring-mvp

# Install CLI in development mode
pip install -e ./agenthub-sdk

# Verify installation
agenthub --version
```

#### Solution 2: Fix Python Path
```bash
# Check Python path
which python

# Check pip path
which pip

# Reinstall with correct pip
python -m pip install -e ./agenthub-sdk
```

#### Solution 3: Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Unix/Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install CLI
pip install -e ./agenthub-sdk
```

### Issue: Dependency Installation Fails

**Symptoms:**
```bash
$ pip install -e ./agenthub-sdk
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**

#### Solution 1: Update pip
```bash
# Update pip
python -m pip install --upgrade pip

# Try installation again
pip install -e ./agenthub-sdk
```

#### Solution 2: Install from requirements
```bash
# Install base requirements first
pip install -r requirements.txt

# Then install CLI
pip install -e ./agenthub-sdk
```

#### Solution 3: Use specific Python version
```bash
# Check Python version
python --version

# Use Python 3.9+ specifically
python3.9 -m pip install -e ./agenthub-sdk
```

## 🖥️ Platform Startup Issues

### Issue: Port Already in Use

**Symptoms:**
```bash
$ python -m server.main --dev
Error: [Errno 48] Address already in use
```

**Solutions:**

#### Solution 1: Find and kill process
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Start server again
python -m server.main --dev
```

#### Solution 2: Use different port
```bash
# Start on different port
python -m server.main --dev --port 8001

# Update CLI configuration
agenthub config set api_url http://localhost:8001
```

#### Solution 3: Check for existing server
```bash
# Check if server is already running
curl http://localhost:8000/health

# If running, you can use it directly
```

### Issue: Database Connection Failed

**Symptoms:**
```bash
$ python -m server.main --dev
Error: database connection failed
```

**Solutions:**

#### Solution 1: Initialize database
```bash
# Initialize database
python -m server.database.init_db

# Start server again
python -m server.main --dev
```

#### Solution 2: Check database file permissions
```bash
# Check database file
ls -la agent_hiring.db

# Fix permissions if needed
chmod 644 agent_hiring.db

# Reset database if corrupted
python -m server.database.init_db --reset
```

#### Solution 3: Check environment variables
```bash
# Check .env file
cat .env

# Ensure database URL is correct
DB_DATABASE_URL=sqlite:///./agent_hiring.db
```

### Issue: Import Errors on Startup

**Symptoms:**
```bash
$ python -m server.main --dev
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**

#### Solution 1: Install server dependencies
```bash
# Install server requirements
pip install -r requirements.txt

# Start server again
python -m server.main --dev
```

#### Solution 2: Check virtual environment
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## 🖥️ CLI Issues

### Issue: CLI Commands Not Working

**Symptoms:**
```bash
$ agenthub agent list
Error: Connection failed
```

**Solutions:**

#### Solution 1: Check platform status
```bash
# Check if platform is running
curl http://localhost:8000/health

# Start platform if not running
python -m server.main --dev
```

#### Solution 2: Check API URL configuration
```bash
# Check current configuration
agenthub config

# Set correct API URL
agenthub config set api_url http://localhost:8000

# Test connection
agenthub status
```

#### Solution 3: Check network connectivity
```bash
# Test basic connectivity
ping localhost

# Test HTTP connectivity
curl -v http://localhost:8000/health
```

### Issue: Authentication Errors

**Symptoms:**
```bash
$ agenthub agent list
Error: Authentication failed
```

**Solutions:**

#### Solution 1: Check API keys
```bash
# Check if API key is set
agenthub config get api_key

# Set API key if needed
agenthub config set api_key your_api_key_here
```

#### Solution 2: Check user permissions
```bash
# Check user status
agenthub user status

# Verify account is active
```

## 💼 Agent Hiring Issues

### Issue: Agent Not Available for Hiring

**Symptoms:**
```bash
$ agenthub hire agent 1
Error: Agent not found or not available
```

**Solutions:**

#### Solution 1: Check agent status
```bash
# List available agents
agenthub agent list

# Get agent details
agenthub agent info 1

# Check if agent is approved
```

#### Solution 2: Check agent approval status
```bash
# If you're the agent creator, approve it
agenthub agent approve 1

# Check approval status
agenthub agent info 1
```

#### Solution 3: Check agent category visibility
```bash
# List agents by category
agenthub agent list --category "research"

# Check if agent is in correct category
```

### Issue: Hiring Fails

**Symptoms:**
```bash
$ agenthub hire agent 1
Error: Hiring failed
```

**Solutions:**

#### Solution 1: Check resource limits
```bash
# Check current resource usage
agenthub resources usage

# Check resource limits
agenthub resources limits

# Increase limits if needed
agenthub resources set-limit --memory 1024
```

#### Solution 2: Check billing status
```bash
# Check billing status
agenthub billing status

# Check available credits
agenthub billing credits
```

#### Solution 3: Check agent configuration
```bash
# Try hiring with minimal config
agenthub hire agent 1 --config '{}'

# Check agent requirements
agenthub agent info 1 --config-options
```

## ⚡ Execution Issues

### Issue: Execution Fails Immediately

**Symptoms:**
```bash
$ agenthub execute hiring hiring_123 --input '{"task": "test"}'
Error: Execution failed
```

**Solutions:**

#### Solution 1: Check hiring status
```bash
# Check hiring status
agenthub hired info hiring_123

# Ensure hiring is active
agenthub hired list --status "active"
```

#### Solution 2: Check deployment status
```bash
# Check deployment
agenthub deploy list

# Start deployment if stopped
agenthub deploy start deploy_123
```

#### Solution 3: Validate input format
```bash
# Check agent input requirements
agenthub agent info <agent_id> --examples

# Use correct input format
agenthub execute hiring hiring_123 --input '{"data": "test"}'
```

### Issue: Execution Hangs or Times Out

**Symptoms:**
```bash
$ agenthub execute hiring hiring_123 --input '{"task": "test"}'
# Command hangs indefinitely
```

**Solutions:**

#### Solution 1: Check execution status
```bash
# In another terminal, check status
agenthub execution list

# Get specific execution status
agenthub execution status exec_123
```

#### Solution 2: Use async execution
```bash
# Execute asynchronously
agenthub execute hiring hiring_123 \
  --input '{"task": "test"}' \
  --async

# Check status later
agenthub execution status exec_123
```

#### Solution 3: Check resource limits
```bash
# Check resource usage
agenthub resources usage

# Increase timeout if needed
agenthub execute hiring hiring_123 \
  --input '{"task": "test"}' \
  --timeout 120
```

### Issue: Execution Returns Errors

**Symptoms:**
```bash
$ agenthub execute hiring hiring_123 --input '{"task": "test"}'
{
  "status": "error",
  "error": "Invalid input format"
}
```

**Solutions:**

#### Solution 1: Check error details
```bash
# Get execution logs
agenthub execution logs exec_123

# Check execution details
agenthub execution status exec_123 --detailed
```

#### Solution 2: Fix input format
```bash
# Check agent requirements
agenthub agent info <agent_id> --examples

# Use correct input format
agenthub execute hiring hiring_123 \
  --input '{"data": {"text": "test", "format": "plain"}}'
```

#### Solution 3: Test with simple input
```bash
# Try with minimal input
agenthub execute hiring hiring_123 \
  --input '{"test": "simple"}'

# Gradually add complexity
```

## 🚀 Deployment Issues

### Issue: Deployment Creation Fails

**Symptoms:**
```bash
$ agenthub deploy create hiring_123
Error: Deployment creation failed
```

**Solutions:**

#### Solution 1: Check hiring status
```bash
# Ensure hiring is active
agenthub hired info hiring_123

# Check hiring status
agenthub hired list --status "active"
```

#### Solution 2: Check resource availability
```bash
# Check available resources
agenthub resources usage

# Check resource limits
agenthub resources limits
```

#### Solution 3: Check deployment configuration
```bash
# Try with minimal config
agenthub deploy create hiring_123 --config '{}'

# Check deployment options
agenthub deploy create --help
```

### Issue: Deployment Won't Start

**Symptoms:**
```bash
$ agenthub deploy start deploy_123
Error: Deployment start failed
```

**Solutions:**

#### Solution 1: Check deployment status
```bash
# Check current status
agenthub deploy status deploy_123

# Check for errors
agenthub deploy status deploy_123 --detailed
```

#### Solution 2: Check resource conflicts
```bash
# Check resource usage
agenthub resources usage --detailed

# Stop conflicting deployments
agenthub deploy list --status "running"
agenthub deploy stop deploy_conflict_123
```

#### Solution 3: Restart deployment
```bash
# Restart deployment
agenthub deploy restart deploy_123

# Check status again
agenthub deploy status deploy_123
```

## 📊 Resource Issues

### Issue: Memory Limit Exceeded

**Symptoms:**
```bash
Error: Memory limit exceeded (512MB)
```

**Solutions:**

#### Solution 1: Increase memory limit
```bash
# Increase memory limit
agenthub resources set-limit --memory 1024

# Check new limits
agenthub resources limits
```

#### Solution 2: Optimize agent usage
```bash
# Check memory usage by hiring
agenthub resources usage --by-hiring

# Stop unused deployments
agenthub deploy list --status "running"
agenthub deploy stop deploy_unused_123
```

#### Solution 3: Use smaller models
```bash
# Hire with smaller model configuration
agenthub hired configure hiring_123 \
  --config '{"model": "gpt-3.5-turbo"}'
```

### Issue: CPU Limit Exceeded

**Symptoms:**
```bash
Error: CPU limit exceeded (2 cores)
```

**Solutions:**

#### Solution 1: Increase CPU limit
```bash
# Increase CPU limit
agenthub resources set-limit --cpu 4

# Check new limits
agenthub resources limits
```

#### Solution 2: Optimize concurrent executions
```bash
# Check concurrent executions
agenthub execution list --status "running"

# Limit concurrent executions
agenthub execute hiring hiring_123 \
  --input '{"task": "test"}' \
  --max-concurrent 1
```

## 🌐 API Issues

### Issue: API Endpoints Not Responding

**Symptoms:**
```bash
$ curl http://localhost:8000/api/agents
Connection refused
```

**Solutions:**

#### Solution 1: Check server status
```bash
# Check if server is running
ps aux | grep "server.main"

# Start server if not running
python -m server.main --dev
```

#### Solution 2: Check server logs
```bash
# Check server console for errors
# Look for error messages in the terminal where server is running
```

#### Solution 3: Check server configuration
```bash
# Check .env file
cat .env

# Verify HOST and PORT settings
HOST=0.0.0.0
PORT=8000
```

### Issue: API Authentication Errors

**Symptoms:**
```bash
$ curl http://localhost:8000/api/agents
{"error": "Authentication required"}
```

**Solutions:**

#### Solution 1: Include API key
```bash
# Use API key in request
curl -H "Authorization: Bearer your_api_key" \
  http://localhost:8000/api/agents
```

#### Solution 2: Check API key validity
```bash
# Verify API key
curl -H "Authorization: Bearer your_api_key" \
  http://localhost:8000/api/auth/verify
```

## ⚡ Performance Issues

### Issue: Slow Agent Execution

**Symptoms:**
- Agent executions take much longer than expected
- Timeouts occur frequently

**Solutions:**

#### Solution 1: Check resource allocation
```bash
# Check resource usage
agenthub resources usage --detailed

# Increase resource limits
agenthub resources set-limit --memory 2048 --cpu 4
```

#### Solution 2: Optimize agent configuration
```bash
# Use faster models
agenthub hired configure hiring_123 \
  --config '{"model": "gpt-3.5-turbo"}'

# Reduce token limits
agenthub hired configure hiring_123 \
  --config '{"max_tokens": 500}'
```

#### Solution 3: Check network latency
```bash
# Test API response time
time curl http://localhost:8000/health

# Check if using local vs remote platform
agenthub config get api_url
```

### Issue: High Resource Usage

**Symptoms:**
- System becomes slow
- Resource limits frequently exceeded

**Solutions:**

#### Solution 1: Monitor resource usage
```bash
# Check current usage
agenthub resources usage --detailed

# Check usage by hiring
agenthub resources usage --by-hiring
```

#### Solution 2: Clean up unused resources
```bash
# Stop unused deployments
agenthub deploy list --status "running"
agenthub deploy stop deploy_unused_123

# Stop completed hirings
agenthub hired list --status "completed"
agenthub hired stop hiring_completed_123
```

#### Solution 3: Set resource alerts
```bash
# Set lower resource limits as warnings
agenthub resources set-limit --memory 512 --cpu 2

# Monitor usage regularly
watch -n 5 'agenthub resources usage'
```

## 🆘 Getting Help

### Self-Diagnosis Steps

1. **Check system status**: `agenthub status`
2. **Check platform health**: `curl http://localhost:8000/health`
3. **Check CLI version**: `agenthub --version`
4. **Check resource usage**: `agenthub resources usage`
5. **Check execution logs**: `agenthub execution logs <id>`

### Documentation Resources

- **[Getting Started Guide](USER_GETTING_STARTED.md)** - First-time setup
- **[User Guide](USER_GUIDE.md)** - Complete user manual
- **[CLI Reference](CLI_REFERENCE.md)** - Command documentation
- **[Examples & Tutorials](EXAMPLES_TUTORIALS.md)** - Practical examples

### Command Help

```bash
# General help
agenthub --help

# Command-specific help
agenthub agent --help
agenthub hire --help
agenthub execute --help

# Subcommand help
agenthub agent list --help
agenthub hire agent --help
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Enable verbose mode
agenthub --verbose agent list

# Check detailed status
agenthub status --detailed

# View execution logs
agenthub execution logs <id> --level debug
```

### Common Error Codes

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `E001` | Connection failed | Check platform status |
| `E002` | Authentication failed | Check API key |
| `E003` | Resource limit exceeded | Increase limits |
| `E004` | Agent not found | Check agent ID |
| `E005` | Hiring failed | Check resource availability |
| `E006` | Execution failed | Check input format |
| `E007` | Deployment failed | Check hiring status |

---

**Still having issues? Check the logs, run diagnostics, and refer to the documentation. Most problems can be resolved with proper troubleshooting! 🔧✨**

*Next: [Examples & Tutorials](EXAMPLES_TUTORIALS.md) - Practical usage examples*
