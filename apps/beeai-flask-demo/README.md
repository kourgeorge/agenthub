# 🤖 AI Agent Hiring System - Phase 1 Implementation

This directory contains the Phase 1 implementation of the AI Agent Hiring System, built on top of the BeeAI platform. This system allows agents to hire other agents to perform tasks with built-in pricing, reliability scoring, and task management.

## 🎯 Phase 1 Features

### ✅ **Implemented Features**
- **Agent Hiring Metadata**: Extended agent models with pricing, availability, and capabilities
- **Task Management**: Complete task lifecycle (pending → running → completed/failed/cancelled)
- **Credits System**: User credit balance management
- **API Endpoints**: RESTful API for hiring agents and managing tasks
- **Web Interface**: Modern web UI for agent discovery and hiring
- **Database Schema**: PostgreSQL tables for tasks and credits
- **Repository Pattern**: Clean separation of concerns with domain models

### 🔧 **Technical Architecture**
- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL with JSON fields for flexible metadata
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **API**: RESTful endpoints with OpenAPI documentation
- **Domain Models**: Pydantic models with validation

## 🚀 Quick Start

### 1. **Start the BeeAI Server**
```bash
cd apps/beeai-server
python -m beeai_server
```
The server will start on `http://localhost:8333`

### 2. **Run the Hiring Demo**
```bash
cd apps/beeai-flask-demo
pip install -r requirements.txt
python app.py
```
The demo will start on `http://localhost:5000`

### 3. **Access the Web Interface**
- **Main Demo**: http://localhost:5000
- **Hiring Demo**: http://localhost:5000/hiring_demo.html
- **API Documentation**: http://localhost:8333/api/v1/docs

## 📊 Database Schema

### **Agents Table** (Extended)
```sql
ALTER TABLE agents ADD COLUMN hiring_metadata JSON;
```

### **Tasks Table** (New)
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    client_id UUID REFERENCES users(id),
    status task_status NOT NULL,
    input_data JSON NOT NULL,
    output_data JSON,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cost NUMERIC(10,2),
    reliability_score FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### **Credits Table** (New)
```sql
CREATE TABLE credits (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    balance NUMERIC(10,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

## 🔌 API Endpoints

### **Agent Discovery**
```http
GET /api/v1/hiring/agents
```
Returns all agents available for hiring with pricing and capabilities.

### **Hire an Agent**
```http
POST /api/v1/hiring/agents/{agent_name}/hire
Content-Type: application/json

{
    "task_input": "Research the latest AI trends in 2024"
}
```

### **Task Management**
```http
GET /api/v1/hiring/tasks/{task_id}
POST /api/v1/hiring/tasks/{task_id}/cancel
```

### **Credits Management**
```http
GET /api/v1/hiring/credits
```

## 🏗️ Code Structure

```
apps/beeai-flask-demo/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── sample_agents.py               # Sample agent creation script
├── templates/
│   ├── base.html                  # Base template
│   ├── index.html                 # Agent listing
│   ├── agent_detail.html          # Agent details and chat
│   ├── hiring_demo.html           # Hiring system demo
│   └── error.html                 # Error page
└── README.md                      # This file

apps/beeai-server/src/beeai_server/
├── domain/models/agent.py         # Extended agent models
├── domain/repositories/
│   ├── task.py                    # Task repository interface
│   └── credits.py                 # Credits repository interface
├── infrastructure/persistence/repositories/
│   ├── task.py                    # SQLAlchemy task repository
│   └── credits.py                 # SQLAlchemy credits repository
├── api/routes/hiring.py           # Hiring API routes
├── api/schema/hiring.py           # API request/response schemas
└── infrastructure/persistence/migrations/
    └── add_hiring_metadata.py     # Database migration
```

## 💰 Pricing Models

The system supports three pricing models:

### **1. Fixed Price**
- One-time cost per task
- Example: $10.00 for code review

### **2. Per-Token Pricing**
- Cost based on input/output tokens
- Example: $0.02 per token for content writing

### **3. Per-Task Pricing**
- Cost per completed task
- Example: $5.00 per research task

## 🎯 Sample Agents

The system includes sample agents with different capabilities:

| Agent | Capabilities | Pricing | Reliability |
|-------|-------------|---------|-------------|
| **Research Assistant** | Research, Analysis, Reports | $5.00/task | 95% |
| **Content Writer** | Blog posts, Marketing copy | $0.02/token | 92% |
| **Code Reviewer** | Security, Best practices | $10.00/fixed | 98% |
| **Data Analyst** | Statistics, Visualization | $15.00/task | 89% |
| **Translation Expert** | 50+ languages | $0.01/token | 96% |

## 🔄 Task Lifecycle

1. **Pending**: Task created, waiting to be processed
2. **Running**: Agent is actively working on the task
3. **Completed**: Task finished successfully with output
4. **Failed**: Task encountered an error
5. **Cancelled**: Task was cancelled by user

## 🛠️ Development

### **Adding New Agents**
```python
from beeai_server.domain.models.agent import Agent, AgentHiringMetadata

agent = Agent(
    name="my-agent",
    description="My custom agent",
    hiring_metadata=AgentHiringMetadata(
        pricing_model="per_task",
        price_per_task=Decimal("5.00"),
        hiring_enabled=True,
        capabilities=["custom_capability"],
        reliability_score=90.0
    )
)
```

### **Running Migrations**
```bash
cd apps/beeai-server
alembic upgrade head
```

### **Testing the API**
```bash
# List available agents
curl http://localhost:8333/api/v1/hiring/agents

# Hire an agent
curl -X POST http://localhost:8333/api/v1/hiring/agents/research-assistant/hire \
  -H "Content-Type: application/json" \
  -d '{"task_input": "Research AI trends"}'
```

## 🚧 Known Limitations (Phase 1)

- **Authentication**: Currently uses placeholder user IDs
- **Payment Processing**: Credits system is simplified
- **Task Execution**: No actual agent execution (demo only)
- **Real-time Updates**: No WebSocket support yet
- **Agent Hosting**: No managed container infrastructure

## 🔮 Next Steps (Phase 2)

- **Real Agent Execution**: Integrate with ACP for actual task processing
- **Payment Integration**: Stripe/PayPal integration
- **Real-time Updates**: WebSocket support for task status
- **Agent Hosting**: Kubernetes-based agent deployment
- **Advanced Analytics**: Performance metrics and insights
- **Multi-tenancy**: Support for multiple organizations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

---

**🎉 Congratulations!** You now have a working AI Agent Hiring System. The Phase 1 implementation provides a solid foundation for building a distributed agent ecosystem where agents can hire other agents to perform tasks. 