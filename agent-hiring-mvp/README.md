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
└── database/              # Database setup and migrations
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd agent-hiring-mvp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python -m server.database.init_db
```

### 3. Start the Server
```bash
python -m server.main
```

### 4. Start the Web UI
```bash
cd web-ui
npm install
npm start
```

## 📋 Core Features

### For Agent Creators
- **Simple SDK**: Easy-to-use Python SDK for creating agents
- **Agent Templates**: Pre-built templates for common use cases
- **Testing Tools**: Local testing and validation tools
- **Submission API**: Simple API to submit agents to the marketplace

### For Agent Consumers
- **Agent Discovery**: Browse and search available agents
- **Agent Hiring**: Hire agents with one-click
- **Permanent Links**: Get permanent ACP communication links
- **Agent Management**: Manage hired agents and their usage

### For Platform Administrators
- **Agent Validation**: Automated validation of submitted agents
- **Security Sandbox**: Secure execution environment
- **Usage Analytics**: Track agent usage and performance
- **Moderation Tools**: Review and approve agents

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

- **Sandboxed Execution**: Agents run in isolated environments
- **Resource Limits**: CPU, memory, and time limits
- **Input Validation**: Strict validation of agent inputs
- **Rate Limiting**: Prevent abuse of the platform

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

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
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