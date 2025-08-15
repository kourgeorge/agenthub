# External Resource Management System

## Overview

The External Resource Management System provides a unified interface for agents to access external resources (LLMs, vector databases, web search) with built-in billing control, usage tracking, and key management.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgentHub Platform                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Agent Runtime │  │ Resource Manager│  │  Billing Engine │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Resource Classes                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │   LLM       │  │ Vector DB   │  │ Web Search  │        │ │
│  │  │ Resources   │  │ Resources   │  │ Resources   │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. **Execution-Based Resource Tracking**
- Every agent execution is tracked with a unique `execution_id`
- All resource usage is recorded per execution
- Detailed cost breakdown for each operation

### 2. **Resource Class Hierarchy**
- All resources inherit from `BaseResource`
- Consistent interface across different providers
- Built-in cost calculation and usage metrics

### 3. **Billing Control**
- User budget management with monthly limits
- Per-request cost limits
- Real-time cost tracking and validation

### 4. **Key Management**
- Secure API key storage and retrieval
- Support for multiple providers per user
- Environment-based fallback for development

## Resource Types

### LLM Resources

#### OpenAI
```python
# Usage
response = await resource_manager.execute_llm_completion(
    provider="openai",
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)

# Cost Calculation
# Input: $0.03 per 1K tokens
# Output: $0.06 per 1K tokens
```

#### Anthropic
```python
# Usage
response = await resource_manager.execute_llm_completion(
    provider="anthropic",
    model="claude-3-sonnet",
    messages=[{"role": "user", "content": "Hello"}]
)

# Cost Calculation
# Input: $0.015 per 1K tokens
# Output: $0.075 per 1K tokens
```

### Vector Database Resources

#### Pinecone
```python
# Usage
results = await resource_manager.execute_vector_search(
    provider="pinecone",
    query_vector=[0.1, 0.2, 0.3],
    top_k=10
)

# Cost Calculation
# Upsert: $0.0001 per vector
# Query: Free
# Delete: Free
```

#### Chroma (Local)
```python
# Usage
results = await resource_manager.execute_vector_search(
    provider="chroma",
    query_texts=["search query"],
    n_results=10
)

# Cost: Free (local deployment)
```

### Web Search Resources

#### Serper
```python
# Usage
results = await resource_manager.execute_web_search(
    provider="serper",
    query="artificial intelligence trends",
    num_results=10
)

# Cost: $0.001 per search
```

#### SerpAPI
```python
# Usage
results = await resource_manager.execute_web_search(
    provider="serpapi",
    query="machine learning news",
    num_results=10
)

# Cost: $0.005 per search
```

#### DuckDuckGo (Free)
```python
# Usage
results = await resource_manager.execute_web_search(
    provider="duckduckgo",
    query="open source AI projects"
)

# Cost: Free
```

## Usage Examples

### Basic Agent with Resources

```python
from server.services.resource_manager import ResourceManager, AgentResourceProxy

class MyAgent:
    def __init__(self, resource_proxy: AgentResourceProxy):
        self.resources = resource_proxy
    
    async def process_request(self, input_data: dict) -> dict:
        # Web search
        search_results = await self.resources.web_search(
            query=input_data['query'],
            provider="serper"
        )
        
        # LLM completion
        analysis = await self.resources.llm_complete(
            provider="openai",
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"Analyze: {search_results}"}
            ]
        )
        
        return {"result": analysis}
```

### Advanced RAG Agent

```python
class RAGAgent:
    def __init__(self, resource_proxy: AgentResourceProxy):
        self.resources = resource_proxy
    
    async def answer_question(self, question: str, documents: List[str]) -> str:
        # Generate embeddings
        embeddings = []
        for doc in documents:
            embedding = await self.resources.llm_embed(
                text=doc,
                provider="openai",
                model="text-embedding-ada-002"
            )
            embeddings.append(embedding)
        
        # Vector search (simplified)
        # In real implementation, store embeddings in vector DB first
        
        # Generate answer
        answer = await self.resources.llm_complete(
            provider="openai",
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"Answer: {question}\nContext: {documents[0]}"}
            ]
        )
        
        return answer
```

## Database Schema

### Execution Tracking
```sql
-- Main execution record
CREATE TABLE executions (
    id INTEGER PRIMARY KEY,
    hiring_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_cost DECIMAL(10,6) DEFAULT 0.0,
    metadata JSON
);

-- Individual resource usage
CREATE TABLE execution_resource_usage (
    id INTEGER PRIMARY KEY,
    execution_id INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_provider VARCHAR(50) NOT NULL,
    resource_model VARCHAR(100),
    operation_type VARCHAR(50) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost DECIMAL(10,6) NOT NULL DEFAULT 0.0,
    request_metadata JSON,
    response_metadata JSON,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Billing Management
```sql
-- User budgets
CREATE TABLE user_budgets (
    user_id INTEGER PRIMARY KEY,
    monthly_budget DECIMAL(10,2) NOT NULL DEFAULT 100.0,
    current_usage DECIMAL(10,2) DEFAULT 0.0,
    reset_date TIMESTAMP NOT NULL,
    max_per_request DECIMAL(10,2) NOT NULL DEFAULT 10.0
);

-- API keys (encrypted)
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    service VARCHAR(50) NOT NULL,
    encrypted_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_used TIMESTAMP
);
```

## Configuration

### Resource Configurations
```python
resource_configs = {
    'openai': {
        'rates': {
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'text-embedding-ada-002': {'input': 0.0001}
        },
        'rate_limits': {'requests_per_minute': 60}
    },
    'anthropic': {
        'rates': {
            'claude-3-sonnet': {'input': 0.015, 'output': 0.075},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125}
        },
        'rate_limits': {'requests_per_minute': 50}
    }
}
```

### Environment Variables
```bash
# OpenAI
OPENAI_API_KEY=your_openai_key

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key

# Pinecone
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_environment

# Serper
SERPER_API_KEY=your_serper_key

# SerpAPI
SERPAPI_API_KEY=your_serpapi_key
```

## Integration with Agent Runtime

### Execution Flow
1. **Start Execution**: Resource manager creates execution record
2. **Resource Access**: Agents use resource proxy for external calls
3. **Usage Tracking**: Each resource call is logged with cost
4. **Budget Validation**: Real-time budget checks before operations
5. **End Execution**: Final cost calculation and summary

### Example Integration
```python
# In agent runtime
async def execute_agent(agent_id: int, input_data: dict, user_id: int):
    # Start execution tracking
    execution_id = generate_execution_id()
    await resource_manager.start_execution(execution_id, user_id)
    
    try:
        # Create resource proxy for agent
        resource_proxy = AgentResourceProxy(resource_manager)
        
        # Execute agent with resources
        result = await agent.main(input_data, resource_proxy)
        
        # End execution
        summary = await resource_manager.end_execution(execution_id, "completed")
        
        return {
            "result": result,
            "execution_summary": summary
        }
        
    except Exception as e:
        await resource_manager.end_execution(execution_id, "failed")
        raise
```

## Benefits

### 1. **Centralized Control**
- All external resource access goes through the system
- Consistent billing and usage tracking
- Easy to add new providers

### 2. **Cost Management**
- Real-time cost tracking
- Budget enforcement
- Detailed usage analytics

### 3. **Security**
- API key management
- Rate limiting
- Access control

### 4. **Scalability**
- Resource pooling
- Efficient connection management
- Load balancing support

### 5. **Developer Experience**
- Simple, consistent API
- Automatic cost calculation
- Built-in error handling

## Future Enhancements

### 1. **Advanced Rate Limiting**
- Redis-based rate limiting
- Per-user rate limits
- Burst handling

### 2. **Resource Pooling**
- Connection pooling for databases
- Client reuse for APIs
- Caching layer

### 3. **Advanced Billing**
- Usage analytics dashboard
- Cost optimization recommendations
- Automated budget alerts

### 4. **Provider Management**
- Dynamic provider switching
- Fallback providers
- Provider health monitoring

### 5. **Security Enhancements**
- Key rotation
- Encryption at rest
- Audit logging 