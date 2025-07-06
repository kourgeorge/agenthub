# AgentHub Database Schema Documentation

This document provides a comprehensive overview of the AgentHub database schema, including table structures, relationships, sample data, and usage patterns.

## Database Overview

The AgentHub system uses a PostgreSQL database with SQLAlchemy ORM. The database consists of 4 main tables that handle the complete agent lifecycle:

1. **Users** - User accounts and profiles
2. **Agents** - Agent definitions and metadata
3. **Hirings** - Agent hiring records and configurations
4. **Executions** - Agent execution logs and results

## Table Structure

### Base Model

All models inherit from a base class that provides common fields:

```python
class Base(DeclarativeBase):
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### 1. Users Table

**Table Name:** `users`

**Purpose:** Store user account information and profiles.

**Schema:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- Basic Information
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    
    -- Authentication
    hashed_password VARCHAR(255),  -- NULL for OAuth users
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Profile
    avatar_url VARCHAR(500),
    bio TEXT,
    website VARCHAR(500),
    
    -- Preferences
    preferences JSON,
    
    -- Timestamps
    last_login_at TIMESTAMP,
    email_verified_at TIMESTAMP
);
```

**Sample Data:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@agenthub.com",
  "full_name": "System Administrator",
  "is_active": true,
  "is_verified": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 2. Agents Table

**Table Name:** `agents`

**Purpose:** Store agent definitions, metadata, and code.

**Schema:**
```sql
CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- Basic Information
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    author VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    
    -- Agent Configuration
    entry_point VARCHAR(255) NOT NULL,  -- e.g., "main.py:AgentClass"
    requirements JSON,  -- List of Python dependencies
    config_schema JSON,  -- JSON schema for agent configuration
    
    -- Agent Code and Assets
    code_zip_url VARCHAR(500),  -- URL to agent code ZIP
    code_hash VARCHAR(64),  -- SHA256 hash of code
    docker_image VARCHAR(255),  -- Docker image name (future)
    code TEXT,  -- Direct code storage
    file_path VARCHAR(500),  -- Path to agent file
    
    -- Metadata
    tags JSON,  -- List of tags
    category VARCHAR(100),
    pricing_model VARCHAR(50),  -- "free", "per_use", "subscription"
    price_per_use FLOAT,
    monthly_price FLOAT,
    
    -- Status and Validation
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    validation_errors JSON,  -- List of validation errors
    
    -- Usage Statistics
    total_hires INTEGER DEFAULT 0 NOT NULL,
    total_executions INTEGER DEFAULT 0 NOT NULL,
    average_rating FLOAT DEFAULT 0.0 NOT NULL
);
```

**Agent Status Values:**
- `draft` - Agent is being created/edited
- `submitted` - Agent submitted for review
- `approved` - Agent approved and ready for use
- `rejected` - Agent rejected during review
- `active` - Agent is active and available
- `inactive` - Agent is temporarily disabled

**Sample Data:**
```json
{
  "id": 1,
  "name": "Echo Agent",
  "description": "A simple agent that echoes back input messages with processing",
  "version": "1.0.0",
  "author": "creator1",
  "email": "creator1@example.com",
  "entry_point": "echo_agent.py:main",
  "requirements": [],
  "tags": ["echo", "simple", "demo"],
  "category": "utility",
  "pricing_model": "free",
  "price_per_use": 0.0,
  "status": "approved",
  "is_public": true,
  "total_hires": 5,
  "total_executions": 25,
  "average_rating": 4.2,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 3. Hirings Table

**Table Name:** `hirings`

**Purpose:** Track agent hiring records and configurations.

**Schema:**
```sql
CREATE TABLE hirings (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- Relationships
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    user_id INTEGER REFERENCES users(id),  -- Optional for anonymous hiring
    
    -- Hiring Details
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    hired_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,  -- NULL for permanent hiring
    
    -- Configuration
    config JSON,  -- Agent-specific configuration
    acp_endpoint VARCHAR(500),  -- ACP communication endpoint
    
    -- Usage Tracking
    total_executions INTEGER DEFAULT 0 NOT NULL,
    last_executed_at TIMESTAMP,
    
    -- Billing (future)
    billing_cycle VARCHAR(20),  -- "monthly", "per_use", "lifetime"
    next_billing_date TIMESTAMP
);
```

**Hiring Status Values:**
- `active` - Hiring is active and can be used
- `expired` - Hiring has expired
- `cancelled` - Hiring was cancelled
- `suspended` - Hiring is temporarily suspended

**Sample Data:**
```json
{
  "id": 1,
  "agent_id": 1,
  "user_id": 2,
  "status": "active",
  "hired_at": "2024-01-01T00:00:00Z",
  "config": {
    "prefix": "Custom Echo: ",
    "timeout": 30
  },
  "total_executions": 10,
  "last_executed_at": "2024-01-01T12:00:00Z",
  "billing_cycle": "per_use",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### 4. Executions Table

**Table Name:** `executions`

**Purpose:** Track agent execution logs and results.

**Schema:**
```sql
CREATE TABLE executions (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- Relationships
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    hiring_id INTEGER REFERENCES hirings(id),
    user_id INTEGER REFERENCES users(id),
    
    -- Execution Details
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,  -- Execution duration in milliseconds
    
    -- Input/Output
    input_data JSON,  -- Input parameters
    output_data JSON,  -- Output results
    error_message TEXT,  -- Error message if failed
    
    -- Resource Usage
    cpu_usage FLOAT,  -- CPU usage percentage
    memory_usage FLOAT,  -- Memory usage in MB
    disk_usage FLOAT,  -- Disk usage in MB
    
    -- Execution Context
    execution_id VARCHAR(64) UNIQUE NOT NULL,  -- Unique execution ID
    acp_session_id VARCHAR(64)  -- ACP session ID
);
```

**Execution Status Values:**
- `pending` - Execution is queued
- `running` - Execution is currently running
- `completed` - Execution completed successfully
- `failed` - Execution failed with error
- `timeout` - Execution timed out
- `cancelled` - Execution was cancelled

**Sample Data:**
```json
{
  "id": 1,
  "agent_id": 1,
  "hiring_id": 1,
  "user_id": 2,
  "status": "completed",
  "started_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:00:01Z",
  "duration_ms": 1000,
  "input_data": {
    "message": "Hello World!",
    "prefix": "Echo: "
  },
  "output_data": {
    "response": "Echo: Hello World!",
    "original_message": "Hello World!",
    "timestamp": "2024-01-01T12:00:00Z",
    "agent_type": "echo"
  },
  "cpu_usage": 2.5,
  "memory_usage": 15.2,
  "execution_id": "exec_1234567890abcdef",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:01Z"
}
```

## Relationships

### Entity Relationship Diagram

```
Users (1) ←→ (N) Hirings (1) ←→ (N) Executions
  ↑                                    ↑
  └──────────── (N) ←→ (1) Agents ←────┘
```

### Relationship Details

1. **User → Hiring** (One-to-Many)
   - A user can hire multiple agents
   - Each hiring record belongs to one user (optional for anonymous)

2. **Agent → Hiring** (One-to-Many)
   - An agent can be hired multiple times
   - Each hiring record is for one specific agent

3. **Hiring → Execution** (One-to-Many)
   - A hiring can have multiple executions
   - Each execution is associated with one hiring (optional for direct execution)

4. **User → Execution** (One-to-Many)
   - A user can have multiple executions
   - Each execution belongs to one user (optional for anonymous)

5. **Agent → Execution** (One-to-Many)
   - An agent can have multiple executions
   - Each execution is for one specific agent

## Sample Data

### Current Sample Agents

The database is initialized with 3 sample agents:

#### 1. Echo Agent
- **Purpose:** Simple echo functionality with message processing
- **Input:** `{"message": "Hello", "prefix": "Echo: "}`
- **Output:** `{"response": "Echo: Hello", "original_message": "Hello", ...}`
- **Status:** Approved and public

#### 2. Calculator Agent
- **Purpose:** Mathematical operations on input data
- **Input:** `{"operation": "add", "numbers": [1, 2, 3]}`
- **Output:** `{"operation": "add", "numbers": [1, 2, 3], "result": 6, ...}`
- **Status:** Approved and public

#### 3. Text Processor Agent
- **Purpose:** Text analysis and processing operations
- **Input:** `{"text": "Hello World", "operation": "analyze"}`
- **Output:** `{"word_count": 2, "character_count": 11, ...}`
- **Status:** Approved and public

### Sample Users

- **admin** - System administrator account
- **creator1** - Agent creator account

## Database Operations

### Common Queries

#### 1. Get All Public Agents
```sql
SELECT * FROM agents 
WHERE is_public = true AND status = 'approved'
ORDER BY total_hires DESC;
```

#### 2. Get User's Hired Agents
```sql
SELECT a.*, h.* FROM agents a
JOIN hirings h ON a.id = h.agent_id
WHERE h.user_id = ? AND h.status = 'active';
```

#### 3. Get Agent Execution History
```sql
SELECT * FROM executions
WHERE agent_id = ?
ORDER BY created_at DESC
LIMIT 100;
```

#### 4. Get Recent Executions for User
```sql
SELECT e.*, a.name as agent_name FROM executions e
JOIN agents a ON e.agent_id = a.id
WHERE e.user_id = ?
ORDER BY e.created_at DESC
LIMIT 50;
```

### Statistics Queries

#### 1. Agent Usage Statistics
```sql
SELECT 
    a.name,
    COUNT(h.id) as total_hirings,
    COUNT(e.id) as total_executions,
    AVG(e.duration_ms) as avg_duration
FROM agents a
LEFT JOIN hirings h ON a.id = h.agent_id
LEFT JOIN executions e ON a.id = e.agent_id
GROUP BY a.id, a.name;
```

#### 2. User Activity
```sql
SELECT 
    u.username,
    COUNT(DISTINCT h.agent_id) as agents_hired,
    COUNT(e.id) as total_executions
FROM users u
LEFT JOIN hirings h ON u.id = h.user_id
LEFT JOIN executions e ON u.id = e.user_id
GROUP BY u.id, u.username;
```

## Database Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/agenthub

# Alternative SQLite for development
DATABASE_URL=sqlite:///./agenthub.db
```

### Database Initialization

```python
from server.database.init_db import init_database, reset_database

# Initialize database with tables and sample data
init_database()

# Reset database (drop all and recreate)
reset_database()
```

## Migration and Schema Changes

### Adding New Fields

1. Update the model class in the appropriate file
2. Create a migration script if needed
3. Update the database initialization if sample data is affected

### Example Migration

```python
# Add new field to Agent model
class Agent(Base):
    # ... existing fields ...
    new_field = Column(String(100), nullable=True)

# Update sample data creation
sample_agents = [
    Agent(
        # ... existing fields ...
        new_field="default_value"
    )
]
```

## Performance Considerations

### Indexes

The following indexes are automatically created:
- Primary keys on all tables
- Foreign key indexes
- `username` and `email` on users table
- `name` on agents table
- `execution_id` on executions table

### Recommended Additional Indexes

```sql
-- For agent discovery
CREATE INDEX idx_agents_status_public ON agents(status, is_public);

-- For execution history
CREATE INDEX idx_executions_agent_created ON executions(agent_id, created_at);

-- For user activity
CREATE INDEX idx_executions_user_created ON executions(user_id, created_at);
```

## Backup and Recovery

### Backup Strategy

```bash
# PostgreSQL backup
pg_dump agenthub > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
cp agenthub.db backup_$(date +%Y%m%d_%H%M%S).db
```

### Recovery

```bash
# PostgreSQL restore
psql agenthub < backup_file.sql

# SQLite restore
cp backup_file.db agenthub.db
```

## Monitoring and Maintenance

### Key Metrics to Monitor

1. **Table Sizes**
   - Monitor growth of executions table
   - Archive old execution logs if needed

2. **Performance**
   - Query execution times
   - Index usage statistics

3. **Data Integrity**
   - Foreign key constraints
   - Unique constraints

### Maintenance Tasks

1. **Regular Cleanup**
   - Archive old execution logs
   - Clean up expired hirings
   - Update usage statistics

2. **Index Maintenance**
   - Rebuild indexes periodically
   - Monitor index usage

3. **Data Validation**
   - Check for orphaned records
   - Validate data consistency

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check DATABASE_URL configuration
   - Verify database server is running

2. **Constraint Violations**
   - Check foreign key relationships
   - Validate unique constraints

3. **Performance Issues**
   - Check query execution plans
   - Monitor index usage
   - Consider query optimization

### Debug Queries

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE tablename IN ('users', 'agents', 'hirings', 'executions');

-- Check for orphaned records
SELECT COUNT(*) FROM executions e
LEFT JOIN agents a ON e.agent_id = a.id
WHERE a.id IS NULL;
```

This database schema provides a solid foundation for the AgentHub platform, supporting the complete lifecycle of agent creation, hiring, and execution with comprehensive tracking and analytics capabilities. 