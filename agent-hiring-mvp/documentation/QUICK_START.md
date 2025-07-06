# 🚀 Quick Start Guide - Agent Hiring System MVP

Get up and running with the Agent Hiring System in under 5 minutes!

## 📋 Prerequisites

- **Python 3.9+** installed on your system
- **Git** for cloning the repository
- **Internet connection** for downloading dependencies

## ⚡ Super Quick Start (Automated)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd agent-hiring-mvp

# Run the automated setup script
python setup.py
```

### 2. Start the Server
```bash
# On Unix/Linux/macOS
./start_server.sh

# On Windows
start_server.bat
```

### 3. Access the System
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Main API**: http://localhost:8000

That's it! 🎉

## 🔧 Manual Setup (Step by Step)

If you prefer to set up manually or the automated script fails:

### 1. Create Virtual Environment
```bash
python -m venv venv

# Activate on Unix/Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python -m server.database.init_db
```

### 4. Start Server
```bash
python -m server.main --dev
```

## 🧪 Test the System

### Run the Test Suite
```bash
python test_system.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/api/agents

# Get API documentation
curl http://localhost:8000/docs
```

## 📝 Create Your First Agent

### 1. Using the Creator SDK
```python
from creator_sdk import AgentConfig, DataProcessingAgent

# Create agent configuration
config = AgentConfig(
    name="My First Agent",
    description="A simple data processing agent",
    author="Your Name",
    email="your.email@example.com",
    entry_point="my_agent.py:MyAgent",
    tags=["data-processing", "example"],
    category="data-science",
)

# Create agent class
class MyAgent(DataProcessingAgent):
    def __init__(self):
        super().__init__(config)
    
    async def process_message(self, message):
        data = message.get("data", {})
        return {
            "status": "success",
            "result": f"Processed: {data}",
        }

# Test locally
agent = MyAgent()
result = await agent.process_message({"data": "Hello World!"})
print(result)
```

### 2. Submit Agent to Platform
```python
from creator_sdk import AgentHiringClient

async def submit_agent():
    async with AgentHiringClient("http://localhost:8000") as client:
        # Create your agent code directory
        # Then submit it
        result = await client.submit_agent(
            agent=MyAgent(),
            code_directory="./my_agent_code"
        )
        print(f"Agent submitted: {result}")

# Run submission
import asyncio
asyncio.run(submit_agent())
```

## 🔍 Explore the System

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API docs |
| `/api/agents` | GET | List available agents |
| `/api/agents/{id}` | GET | Get agent details |
| `/api/agents/submit` | POST | Submit new agent |
| `/api/hiring/hire/{id}` | POST | Hire an agent |
| `/api/hiring/my-agents` | GET | List hired agents |

### Sample API Calls

#### List Agents
```bash
curl -X GET "http://localhost:8000/api/agents" \
  -H "accept: application/json"
```

#### Submit Agent
```bash
curl -X POST "http://localhost:8000/api/agents/submit" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "name=Test Agent" \
  -F "description=A test agent" \
  -F "author=Test Author" \
  -F "email=test@example.com" \
  -F "entry_point=main.py:TestAgent" \
  -F "code_file=@agent_code.zip"
```

#### Hire Agent
```bash
curl -X POST "http://localhost:8000/api/hiring/hire/1" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"config": {"setting": "value"}}'
```

## 🛠️ Development

### Project Structure
```
agent-hiring-mvp/
├── server/              # FastAPI backend
├── creator-sdk/         # SDK for agent creators
├── agent-runtime/       # Agent execution engine
├── web-ui/             # React frontend (future)
└── tests/              # Test suite
```

### Key Files
- `server/main.py` - Main FastAPI application
- `server/models/` - Database models
- `server/services/` - Business logic
- `creator-sdk/agent.py` - Agent base classes
- `test_system.py` - Comprehensive tests

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=server --cov=creator_sdk
```

## 🔧 Configuration

### Environment Variables
The system uses a `.env` file for configuration:

```env
# Database
DB_DATABASE_URL=sqlite:///./agent_hiring.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here

# Agent Runtime
AGENT_TIMEOUT_SECONDS=300
AGENT_MEMORY_LIMIT_MB=512
```

### Database
- **Development**: SQLite (default)
- **Production**: PostgreSQL (configure in `.env`)

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process or use a different port
python -m server.main --port 8001
```

#### 2. Database Errors
```bash
# Reset the database
python -m server.database.init_db --reset
```

#### 3. Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 4. Permission Errors
```bash
# Make startup script executable
chmod +x start_server.sh
```

### Getting Help

1. **Check the logs**: Look for error messages in the console
2. **Verify setup**: Run `python test_system.py` to check system health
3. **Check API docs**: Visit http://localhost:8000/docs for endpoint details
4. **Review configuration**: Ensure `.env` file is properly configured

## 📚 Next Steps

### For Agent Creators
1. **Learn the SDK**: Study `creator-sdk/examples/` for agent patterns
2. **Build an agent**: Create your first agent using the templates
3. **Test locally**: Use the test suite to validate your agent
4. **Submit to platform**: Use the API to submit your agent

### For Platform Administrators
1. **Review submissions**: Use the API to approve/reject agents
2. **Monitor system**: Check logs and database for system health
3. **Configure security**: Update `.env` with production settings
4. **Scale deployment**: Consider Docker/containerization for production

### For Agent Consumers
1. **Browse agents**: Use the API to discover available agents
2. **Hire agents**: Submit hiring requests via API
3. **Communicate**: Use ACP protocol for agent communication
4. **Monitor usage**: Track execution metrics and costs

## 🎯 What's Next?

The MVP provides a solid foundation. Future enhancements include:

- **Web UI**: React frontend for user interface
- **Authentication**: JWT-based user authentication
- **Payment Integration**: Stripe/PayPal for billing
- **Advanced Analytics**: Usage analytics and insights
- **Docker Support**: Containerized deployment
- **Kubernetes**: Orchestration and scaling

## 📞 Support

- **Documentation**: Check `PROJECT_STRUCTURE.md` for detailed architecture
- **API Docs**: Interactive docs at http://localhost:8000/docs
- **Examples**: Study `creator-sdk/examples/` for agent patterns
- **Tests**: Run `test_system.py` for system validation

---

**Happy Agent Building! 🤖✨** 