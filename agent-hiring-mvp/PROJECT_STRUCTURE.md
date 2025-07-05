# Agent Hiring System MVP - Project Structure

This document provides a comprehensive overview of the project structure and architecture.

## 📁 Directory Structure

```
agent-hiring-mvp/
├── README.md                    # Main project documentation
├── PROJECT_STRUCTURE.md         # This file - detailed structure overview
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── setup.py                    # Automated setup script
├── test_system.py              # Comprehensive test script
├── .env                        # Environment variables (created by setup)
├── .gitignore                  # Git ignore rules
│
├── server/                     # FastAPI backend server
│   ├── __init__.py
│   ├── main.py                 # Main FastAPI application
│   │
│   ├── api/                    # REST API endpoints
│   │   ├── __init__.py
│   │   ├── agents.py           # Agent management endpoints
│   │   ├── hiring.py           # Hiring management endpoints
│   │   ├── execution.py        # Agent execution endpoints
│   │   └── acp.py              # ACP protocol endpoints
│   │
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py           # Application configuration
│   │   ├── security.py         # Security utilities
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── base.py             # Base model class
│   │   ├── agent.py            # Agent model
│   │   ├── hiring.py           # Hiring model
│   │   ├── execution.py        # Execution model
│   │   └── user.py             # User model
│   │
│   ├── services/               # Business services
│   │   ├── __init__.py
│   │   ├── agent_service.py    # Agent management service
│   │   ├── hiring_service.py   # Hiring management service
│   │   ├── execution_service.py # Agent execution service
│   │   └── acp_service.py      # ACP protocol service
│   │
│   ├── database/               # Database configuration
│   │   ├── __init__.py
│   │   ├── config.py           # Database configuration
│   │   └── init_db.py          # Database initialization
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── file_utils.py       # File handling utilities
│       ├── validation.py       # Validation utilities
│       └── logging.py          # Logging configuration
│
├── agent-runtime/              # Agent execution engine
│   ├── __init__.py
│   ├── executor/               # Agent execution logic
│   │   ├── __init__.py
│   │   ├── base.py             # Base executor
│   │   ├── python.py           # Python agent executor
│   │   └── docker.py           # Docker agent executor
│   │
│   ├── sandbox/                # Security sandbox
│   │   ├── __init__.py
│   │   ├── base.py             # Base sandbox
│   │   ├── python_sandbox.py   # Python sandbox
│   │   └── docker_sandbox.py   # Docker sandbox
│   │
│   └── acp/                    # ACP protocol implementation
│       ├── __init__.py
│       ├── protocol.py         # ACP protocol definition
│       ├── server.py           # ACP server
│       └── client.py           # ACP client
│
├── creator-sdk/                # SDK for agent creators
│   ├── __init__.py
│   ├── agent.py                # Agent base classes
│   ├── client.py               # API client
│   ├── templates.py            # Agent templates
│   │
│   ├── examples/               # Example agents
│   │   ├── __init__.py
│   │   ├── data_analyzer_agent.py
│   │   ├── chat_assistant_agent.py
│   │   └── code_reviewer_agent.py
│   │
│   └── templates/              # Agent templates
│       ├── __init__.py
│       ├── basic_agent.py      # Basic agent template
│       ├── data_agent.py       # Data processing template
│       └── chat_agent.py       # Chat agent template
│
├── web-ui/                     # React frontend (future)
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── utils/
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   └── test_api.py
│   │
│   ├── integration/            # Integration tests
│   │   ├── __init__.py
│   │   ├── test_agent_submission.py
│   │   └── test_hiring_flow.py
│   │
│   └── e2e/                    # End-to-end tests
│       ├── __init__.py
│       └── test_full_workflow.py
│
├── docs/                       # Documentation
│   ├── api.md                  # API documentation
│   ├── deployment.md           # Deployment guide
│   └── development.md          # Development guide
│
├── scripts/                    # Utility scripts
│   ├── start_server.sh         # Server startup script
│   ├── start_server.bat        # Windows startup script
│   └── deploy.sh               # Deployment script
│
├── uploads/                    # File uploads (created by setup)
├── logs/                       # Log files (created by setup)
├── temp/                       # Temporary files (created by setup)
└── agent_hiring.db             # SQLite database (created by setup)
```

## 🏗️ Architecture Overview

### Backend Architecture (FastAPI)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   API Routes    │    │   Services      │
│                 │    │                 │    │                 │
│  - CORS         │◄──►│  - Agents       │◄──►│  - AgentService │
│  - Middleware   │    │  - Hiring       │    │  - HiringService│
│  - Exception    │    │  - Execution    │    │  - ExecutionSvc  │
│  - Logging      │    │  - ACP          │    │  - ACPService    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Database      │
                       │                 │
                       │  - SQLAlchemy   │
                       │  - Models       │
                       │  - Migrations   │
                       └─────────────────┘
```

### Agent Runtime Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Request   │    │   Agent Runtime │    │   Sandbox       │
│                 │    │                 │    │                 │
│  - Execute      │───►│  - Executor     │───►│  - Security     │
│  - Status       │    │  - Loader       │    │  - Isolation    │
│  - Results      │    │  - Runner       │    │  - Limits       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   ACP Protocol  │
                       │                 │
                       │  - WebSocket    │
                       │  - Message      │
                       │  - Routing      │
                       └─────────────────┘
```

### Creator SDK Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent Code    │    │   Creator SDK   │    │   API Client    │
│                 │    │                 │    │                 │
│  - Agent Class  │───►│  - Base Classes │───►│  - HTTP Client  │
│  - Config       │    │  - Templates    │    │  - Validation   │
│  - Dependencies │    │  - Utilities    │    │  - Submission   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Key Components

### 1. Server (FastAPI Backend)

**Main Application (`server/main.py`)**
- FastAPI application setup
- CORS middleware configuration
- Router registration
- Exception handling
- Health check endpoints

**API Endpoints (`server/api/`)**
- `agents.py`: Agent CRUD operations
- `hiring.py`: Hiring management
- `execution.py`: Agent execution
- `acp.py`: ACP protocol endpoints

**Database Models (`server/models/`)**
- `Agent`: Agent metadata and configuration
- `Hiring`: Hiring records and status
- `Execution`: Execution logs and metrics
- `User`: User accounts (future)

**Services (`server/services/`)**
- `AgentService`: Agent lifecycle management
- `HiringService`: Hiring workflow
- `ExecutionService`: Agent execution
- `ACPService`: ACP protocol handling

### 2. Agent Runtime

**Executor (`agent-runtime/executor/`)**
- Python agent execution
- Docker container execution (future)
- Resource monitoring
- Timeout handling

**Sandbox (`agent-runtime/sandbox/`)**
- Security isolation
- Resource limits
- File system restrictions
- Network access control

**ACP Protocol (`agent-runtime/acp/`)**
- WebSocket communication
- Message routing
- Session management
- Protocol compliance

### 3. Creator SDK

**Base Classes (`creator-sdk/agent.py`)**
- `Agent`: Abstract base class
- `AgentConfig`: Configuration dataclass
- `SimpleAgent`: Basic implementation
- `DataProcessingAgent`: Data-focused agent
- `ChatAgent`: Conversation agent

**Client (`creator-sdk/client.py`)**
- `AgentHiringClient`: API client
- Agent submission
- Code packaging
- Validation

**Examples (`creator-sdk/examples/`)**
- `DataAnalyzerAgent`: Data analysis example
- `ChatAssistantAgent`: Chat bot example
- `CodeReviewerAgent`: Code review example

### 4. Database Schema

**Core Tables**
```sql
-- Agents table
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    version VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    entry_point VARCHAR(255) NOT NULL,
    requirements JSON,
    config_schema JSON,
    tags JSON,
    category VARCHAR(100),
    pricing_model VARCHAR(50),
    price_per_use FLOAT,
    monthly_price FLOAT,
    status VARCHAR(20) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    validation_errors JSON,
    total_hires INTEGER DEFAULT 0,
    total_executions INTEGER DEFAULT 0,
    average_rating FLOAT DEFAULT 0.0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Hiring table
CREATE TABLE hirings (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER NOT NULL,
    user_id INTEGER,
    status VARCHAR(20) NOT NULL,
    hired_at DATETIME NOT NULL,
    expires_at DATETIME,
    config JSON,
    acp_endpoint VARCHAR(500),
    total_executions INTEGER DEFAULT 0,
    last_executed_at DATETIME,
    billing_cycle VARCHAR(20),
    next_billing_date DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Executions table
CREATE TABLE executions (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER NOT NULL,
    hiring_id INTEGER,
    user_id INTEGER,
    status VARCHAR(20) NOT NULL,
    started_at DATETIME,
    completed_at DATETIME,
    duration_ms INTEGER,
    input_data JSON,
    output_data JSON,
    error_message TEXT,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_usage FLOAT,
    execution_id VARCHAR(64) UNIQUE NOT NULL,
    acp_session_id VARCHAR(64),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents (id),
    FOREIGN KEY (hiring_id) REFERENCES hirings (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    avatar_url VARCHAR(500),
    bio TEXT,
    website VARCHAR(500),
    preferences JSON,
    last_login_at DATETIME,
    email_verified_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## 🚀 Getting Started

### 1. Quick Setup
```bash
# Clone the repository
git clone <repository-url>
cd agent-hiring-mvp

# Run automated setup
python setup.py

# Start the server
./start_server.sh  # Unix/Linux/macOS
# or
start_server.bat   # Windows
```

### 2. Manual Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix/Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m server.database.init_db

# Start server
python -m server.main --dev
```

### 3. Testing
```bash
# Run comprehensive tests
python test_system.py

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 📚 API Documentation

Once the server is running, visit:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔄 Development Workflow

### For Agent Creators
1. Use the Creator SDK to build agents
2. Test agents locally
3. Submit agents via API
4. Monitor agent performance

### For Platform Administrators
1. Review submitted agents
2. Approve/reject agents
3. Monitor system health
4. Manage user accounts

### For Agent Consumers
1. Browse available agents
2. Hire agents
3. Communicate via ACP
4. Monitor usage and costs

## 🛡️ Security Features

- **Sandboxed Execution**: Agents run in isolated environments
- **Resource Limits**: CPU, memory, and time restrictions
- **Input Validation**: Strict validation of all inputs
- **Rate Limiting**: Prevent abuse of the platform
- **Secure Communication**: ACP protocol with authentication

## 📈 Scalability Considerations

- **Database**: SQLite for development, PostgreSQL for production
- **Caching**: Redis for session management and caching
- **Load Balancing**: Multiple server instances
- **Monitoring**: Prometheus metrics and logging
- **Containerization**: Docker support for deployment

## 🔮 Future Enhancements

- **Web UI**: React frontend for user interface
- **Authentication**: JWT-based user authentication
- **Payment Integration**: Stripe/PayPal for billing
- **Advanced Analytics**: Usage analytics and insights
- **Multi-language Support**: Internationalization
- **Mobile App**: React Native mobile application 