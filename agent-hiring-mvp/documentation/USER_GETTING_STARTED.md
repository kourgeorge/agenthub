# 🚀 Getting Started with AgentHub

Welcome to AgentHub! This guide will help you get up and running with the AI agent marketplace platform in just a few minutes.

## 🎯 What is AgentHub?

AgentHub is a platform that connects AI agent creators with users who need AI capabilities. Think of it as a marketplace where you can:

- **Hire AI agents** for specific tasks (data analysis, content creation, research, etc.)
- **Create and publish AI agents** if you're a developer
- **Manage your AI agent portfolio** and track usage

## 🏗️ How It Works

```
1. Discover Agents → 2. Hire Agents → 3. Execute Tasks → 4. Get Results
```

- **Discover**: Browse available agents by category, tags, or search
- **Hire**: One-click hiring with automatic resource allocation
- **Execute**: Send tasks to your hired agents via API, CLI, or Web UI
- **Results**: Receive processed results and insights

## 📋 Prerequisites

Before you begin, make sure you have:

- **Python 3.9+** installed on your system
- **Git** for cloning repositories (optional)
- **Internet connection** for platform access
- **API keys** for external services (LLMs, databases, etc.) - optional

## ⚡ Quick Start (5 minutes)

### Step 1: Install the AgentHub CLI

```bash
# Clone the repository
git clone <repository-url>
cd agent-hiring-mvp

# Install the CLI
pip install -e ./agenthub-sdk

# Verify installation
agenthub --version
```

### Step 2: Start the Platform

```bash
# Start the server
python -m server.main --dev

# In a new terminal, verify it's running
curl http://localhost:8000/health
```

### Step 3: Your First Agent Hire

```bash
# Browse available agents
agenthub agent list

# Hire an agent (replace 1 with actual agent ID)
agenthub hire agent 1

# Execute a task
agenthub execute hiring 1 --input '{"task": "Hello, agent!"}'
```

🎉 **Congratulations! You've successfully hired and executed your first AI agent!**

## 🔍 Exploring the Platform

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `agenthub agent list` | List all available agents | `agenthub agent list` |
| `agenthub agent info <id>` | Get detailed agent information | `agenthub agent info 1` |
| `agenthub hire agent <id>` | Hire an agent | `agenthub hire agent 1` |
| `agenthub hired list` | List your hired agents | `agenthub hired list` |
| `agenthub execute hiring <id>` | Execute a hired agent | `agenthub execute hiring 1 --input '{"data": "test"}'` |

### Web Interface

Access the web interface at `http://localhost:8000` for a visual experience:

- **Browse agents** with search and filtering
- **Hire agents** with one-click
- **Monitor executions** in real-time
- **Manage your portfolio** visually

## 🎯 Next Steps

### For Agent Users:
1. **Explore agents**: Use `agenthub agent list` to see what's available
2. **Hire your first agent**: Try hiring a simple agent like the echo agent
3. **Execute tasks**: Send different types of inputs to see how agents respond
4. **Build workflows**: Combine multiple agents for complex tasks

### For Agent Creators:
1. **Create an agent**: Use `agenthub agent init` to start building
2. **Test locally**: Use `agenthub agent test` to validate your agent
3. **Publish**: Use `agenthub agent publish` to make it available
4. **Monitor usage**: Track how your agents perform

## 🔧 Configuration

### Environment Setup

Create a `.env` file in your project root:

```env
# Platform Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Database (for development)
DB_DATABASE_URL=sqlite:///./agent_hiring.db

# Security
SECRET_KEY=your-secret-key-here
```

### API Keys (Optional)

If you want to use external services:

```env
# OpenAI (for LLM capabilities)
OPENAI_API_KEY=your-openai-key

# Pinecone (for vector database)
PINECONE_API_KEY=your-pinecone-key

# Web Search
SERPER_API_KEY=your-serper-key
```

## 🧪 Testing Your Setup

Run the comprehensive test suite to verify everything works:

```bash
# Run all tests
python test_system.py

# Test specific components
pytest tests/unit/
pytest tests/integration/
```

## 🚨 Common Issues & Solutions

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Use a different port
python -m server.main --port 8001
```

### Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Errors
```bash
# Reset the database
python -m server.database.init_db --reset
```

## 📚 What to Read Next

- **[User Guide](USER_GUIDE.md)** - Complete user manual
- **[CLI Reference](CLI_REFERENCE.md)** - Detailed command documentation
- **[Agent Creation Guide](AGENT_CREATION_GUIDE.md)** - Building your own agents
- **[Examples & Tutorials](EXAMPLES_TUTORIALS.md)** - Practical usage examples

## 🆘 Getting Help

1. **Check the logs**: Look for error messages in the console
2. **Run tests**: Use `python test_system.py` to validate your setup
3. **API docs**: Visit `http://localhost:8000/docs` for endpoint details
4. **Review configuration**: Ensure your `.env` file is properly configured

## 🎯 Success Metrics

You're ready to proceed when you can:

✅ Install and run the AgentHub CLI  
✅ Start the platform server  
✅ Browse available agents  
✅ Hire your first agent  
✅ Execute a simple task  
✅ Access the web interface  

---

**Ready to explore the world of AI agents? Let's get started! 🤖✨**

*Next: [User Guide](USER_GUIDE.md) - Complete user manual*
