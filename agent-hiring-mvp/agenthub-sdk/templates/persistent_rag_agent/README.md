# Persistent RAG Agent

A demonstration of the new persistent agent architecture in AgentHub, featuring separate initialization and execution phases.

## 🚀 New Persistent Agent Architecture

This agent demonstrates the new persistent agent capabilities in AgentHub:

### **Key Features**
- **Separate Initialization and Execution**: Expensive setup happens once, not per execution
- **Persistent State**: Agent state persists between executions
- **Resource Efficiency**: Better memory and resource management
- **Backward Compatibility**: Works with existing AgentHub infrastructure

### **Lifecycle Phases**

1. **Initialization Phase** (`initialize_rag`)
   - Load and index website content
   - Create vector embeddings
   - Setup LLM and QA chain
   - Save state to persistent storage

2. **Execution Phase** (`execute_rag`)
   - Load existing state
   - Execute RAG queries
   - Return answers based on indexed content

3. **Cleanup Phase** (`cleanup_rag`)
   - Clean up resources
   - Remove persistent state
   - Free memory

## 📋 Usage

### **With AgentHub CLI**

```bash
# 1. Initialize the agent (happens once)
agenthub hire agent <agent_id> --init-config '{"website_url": "https://example.com", "model_name": "gpt-4"}'

# 2. Execute queries (can be called multiple times)
agenthub execute <hiring_id> --input '{"question": "What is this website about?"}'
agenthub execute <hiring_id> --input '{"question": "What are the main features?"}'

# 3. Clean up when done
agenthub terminate <hiring_id>
```

### **With API**

```python
# 1. Initialize
POST /agents/{agent_id}/initialize
{
  "config": {
    "website_url": "https://example.com",
    "model_name": "gpt-4",
    "temperature": 0
  }
}

# 2. Execute
POST /execution/{execution_id}/run
{
  "input_data": {
    "question": "What is this website about?"
  }
}

# 3. Clean up
DELETE /hiring/{hiring_id}
```

### **Direct Usage**

```python
from persistent_rag_agent import main

# Initialize
init_result = main(
    {"website_url": "https://example.com"}, 
    {"agent_id": "my_rag_agent"}
)

# Execute queries
exec_result = main(
    {"question": "What is this website about?"}, 
    {"agent_id": "my_rag_agent"}
)

# Clean up
cleanup_result = main(
    {"action": "cleanup"}, 
    {"agent_id": "my_rag_agent"}
)
```

## 🏗️ Architecture

### **State Management**
- **File-based Storage**: State stored in `/tmp/agenthub_agent_states/`
- **Serialization**: Uses pickle for state persistence
- **Vectorstore**: FAISS embeddings stored separately
- **Automatic Cleanup**: Resources cleaned up on termination

### **Configuration Schema**
The agent supports different configuration schemas for each phase:

```json
{
  "config_schema": {
    "initialize": {
      "website_url": "string (required)",
      "model_name": "choice",
      "temperature": "number",
      "chunk_size": "integer",
      "chunk_overlap": "integer"
    },
    "execute": {
      "question": "string (required)"
    }
  }
}
```

### **Backward Compatibility**
The agent maintains full backward compatibility with existing AgentHub agents:

- Single `main()` function entry point
- Automatic phase detection based on input
- Fallback to legacy execution mode

## 🔧 Configuration Options

### **Initialization Parameters**
- `website_url`: URL to index (required)
- `model_name`: OpenAI model to use (gpt-3.5-turbo, gpt-4, gpt-4o)
- `temperature`: Response creativity (0-2)
- `chunk_size`: Text chunk size for processing (100-4000)
- `chunk_overlap`: Overlap between chunks (0-1000)

### **Execution Parameters**
- `question`: Question to ask about indexed content (required)

## 📊 Performance Benefits

### **Before (Traditional Agent)**
```
Execution 1: Load website → Create embeddings → Query → Answer (30s)
Execution 2: Load website → Create embeddings → Query → Answer (30s)
Execution 3: Load website → Create embeddings → Query → Answer (30s)
Total: 90 seconds
```

### **After (Persistent Agent)**
```
Initialization: Load website → Create embeddings → Save state (30s)
Execution 1: Load state → Query → Answer (2s)
Execution 2: Load state → Query → Answer (2s)
Execution 3: Load state → Query → Answer (2s)
Total: 36 seconds (60% improvement)
```

## 🛠️ Development

### **Adding New Persistent Agents**

1. **Create agent class**:
```python
class MyPersistentAgent:
    def initialize(self, config, agent_id):
        # Setup expensive resources
        pass
    
    def execute(self, input_data, config, agent_id):
        # Use existing resources
        pass
    
    def cleanup(self, config, agent_id):
        # Clean up resources
        pass
```

2. **Define lifecycle functions**:
```python
def initialize_my_agent(config, agent_id):
    return agent.initialize(config, agent_id)

def execute_my_agent(input_data, config, agent_id):
    return agent.execute(input_data, config, agent_id)

def cleanup_my_agent(config, agent_id):
    return agent.cleanup(config, agent_id)
```

3. **Update config.json**:
```json
{
  "agent_type": "persistent",
  "lifecycle": {
    "initialize": "initialize_my_agent",
    "execute": "execute_my_agent",
    "cleanup": "cleanup_my_agent"
  }
}
```

## 🔍 Troubleshooting

### **Common Issues**

1. **State not found**: Ensure agent was properly initialized
2. **Memory issues**: Check available RAM for large documents
3. **API rate limits**: Monitor OpenAI API usage
4. **File permissions**: Ensure write access to `/tmp/agenthub_agent_states/`

### **Debug Mode**
Enable debug logging by setting environment variable:
```bash
export AGENTHUB_DEBUG=1
```

## 📈 Future Enhancements

- **Database-backed state storage**
- **Distributed state management**
- **State versioning and rollback**
- **Automatic state cleanup**
- **State sharing between agents**

## 🤝 Contributing

This agent serves as a reference implementation for the new persistent agent architecture. Contributions are welcome to improve the implementation and add new features. 