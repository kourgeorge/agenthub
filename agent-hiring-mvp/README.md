# AI Agent Hiring System MVP

A complete MVP for hiring, managing, and communicating with AI agents through a simple API and web interface.

## 🏗️ Architecture

```
agent-hiring-mvp/
├── server/                 # FastAPI backend server
│   ├── api/               # REST API endpoints
│   ├── core/              # Core business logic
│   ├── models/            # Database models
│   ├── services/          # Business services
│   └── utils/             # Utilities
├── agent-runtime/         # Agent execution engine
│   ├── executor/          # Agent execution logic
│   ├── sandbox/           # Security sandbox
│   └── acp/               # ACP protocol implementation
├── creator-sdk/           # SDK for agent creators
│   ├── examples/          # Example agents
│   └── templates/         # Agent templates
├── web-ui/                # React frontend
│   ├── components/        # UI components
│   └── pages/             # Page components
└── database/              # Database setup
```

## 🚀 Quick Start

### 📚 **New to AgentHub? Start Here!**
- **[Getting Started Guide](documentation/USER_GETTING_STARTED.md)** - Complete setup in 5 minutes
- **[User Guide](documentation/USER_GUIDE.md)** - Full platform usage manual
- **[Examples & Tutorials](documentation/EXAMPLES_TUTORIALS.md)** - Practical usage examples

### 🔧 **Technical Setup**
1. **Setup Environment**
```bash
cd agent-hiring-mvp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Initialize Database**
```bash
python -m server.database.init_db
```

3. **Start the Server**
```bash
python -m server.main
```

4. **Start the Web UI**
```bash
cd web-ui
npm install
npm start
```

### 🎯 **First Steps**
```bash
# Install CLI
pip install -e ./agenthub-sdk

# Browse agents
agenthub agent list

# Hire your first agent
agenthub hire agent 1

# Execute a task
agenthub execute hiring <hiring_id> --input '{"task": "Hello!"}'
```

## 📋 Core Features

### For Agent Creators
- **Simple SDK**: Easy-to-use Python SDK for creating agents
- **Agent Templates**: Pre-built templates for common use cases
- **Testing Tools**: Local testing and validation tools
- **Submission API**: Simple API to submit agents to the marketplace
- **Code Storage**: Direct code storage in database or file paths

### For Agent Consumers
- **Agent Discovery**: Browse and search available agents
- **Agent Hiring**: Hire agents with one-click
- **Real Execution**: Execute actual agent code with input/output handling
- **Permanent Links**: Get permanent ACP communication links
- **Agent Management**: Manage hired agents and their usage

### For Platform Administrators
- **Agent Validation**: Automated validation of submitted agents
- **Secure Runtime**: Subprocess-based execution with security measures
- **Resource Management**: CPU, memory, and time limits enforcement
- **Usage Analytics**: Track agent usage and performance
- **Moderation Tools**: Review and approve agents

### For Billing & Payments
- **Usage Tracking**: Automatic tracking of agent execution costs
- **Invoice Generation**: Monthly invoices based on usage
- **Payment Processing**: Secure Stripe integration for payments
- **Payment Method Management**: Secure credit card management UI
- **Billing Dashboard**: Comprehensive billing and usage analytics

## 🔧 API Endpoints

### Agent Management
- `POST /api/agents/submit` - Submit a new agent
- `GET /api/agents` - List available agents
- `GET /api/agents/{agent_id}` - Get agent details
- `PUT /api/agents/{agent_id}/approve` - Approve agent
- `DELETE /api/agents/{agent_id}` - Delete agent

### Agent Hiring
- `POST /api/hiring/hire/{agent_id}` - Hire an agent
- `GET /api/hiring/my-agents` - List hired agents
- `GET /api/hiring/{hiring_id}/acp-link` - Get ACP communication link

### Agent Execution
- `POST /api/agents/{agent_id}/execute` - Execute agent
- `GET /api/agents/{agent_id}/status` - Get execution status

## 🛡️ Security Features

- **Secure Runtime**: Subprocess-based execution with controlled environment
- **Resource Limits**: CPU, memory (100MB), and time (30s) limits
- **Security Checks**: Detection of forbidden commands and suspicious patterns
- **Input Validation**: Strict validation of agent inputs and outputs
- **Rate Limiting**: Prevent abuse of the platform
- **Code Isolation**: Temporary execution directories with cleanup

## 📊 Database Schema

### Core Tables
- `agents` - Agent metadata and code
- `hiring` - Agent hiring records
- `executions` - Agent execution logs
- `users` - User accounts (future)
- `payments` - Payment records (future)

## 🔌 ACP Integration

The system implements the Agent Communication Protocol (ACP) to provide:
- Standardized agent communication
- Permanent communication links
- Message routing and delivery
- Agent state management

## 📚 Documentation

### 🎯 **User Documentation**
- **[Getting Started Guide](documentation/USER_GETTING_STARTED.md)** - First-time setup and quick start
- **[User Guide](documentation/USER_GUIDE.md)** - Complete user manual
- **[CLI Reference](documentation/CLI_REFERENCE.md)** - Command-line interface documentation
- **[Examples & Tutorials](documentation/EXAMPLES_TUTORIALS.md)** - Practical usage examples
- **[Troubleshooting Guide](documentation/TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions

### 🏗️ **Technical Documentation**
- **[Documentation Index](documentation/README.md)** - Complete documentation overview
- **[Business Overview](documentation/AGENTHUB_BUSINESS_OVERVIEW.md)** - Platform vision and business model
- **[Project Structure](documentation/PROJECT_STRUCTURE.md)** - Codebase organization
- **[Database Schema](documentation/DATABASE_SCHEMA.md)** - Database design
- **[Security](documentation/SECURITY_IMPROVEMENTS.md)** - Security features and best practices

### 🔍 **Finding Help**
- **New users**: Start with [Getting Started Guide](documentation/USER_GETTING_STARTED.md)
- **CLI users**: Reference [CLI Reference](documentation/CLI_REFERENCE.md)
- **Troubleshooting**: Check [Troubleshooting Guide](documentation/TROUBLESHOOTING_GUIDE.md)
- **API users**: Visit `/docs` endpoint for interactive API documentation

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Test real agent execution
python test_real_agents.py
```

## 📈 Deployment

### Development
```bash
python -m server.main --dev
```

### Production
```bash
# Using Docker
docker-compose up -d

# Using systemd
sudo systemctl start agent-hiring
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details 