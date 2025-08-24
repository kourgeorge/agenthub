# Persistent RAG Agent

This agent demonstrates the new **JSON Schema format** for AgentHub persistent agents. It shows how to define clear input and output schemas using the flat JSON Schema structure while maintaining the persistent agent lifecycle.

## 🆕 What's New: JSON Schema Format

The JSON Schema format provides:
- **Clear Input/Output Contracts**: Define exactly what your agent expects and returns
- **Runtime Validation**: Automatic validation of inputs and outputs during execution
- **Better Developer Experience**: Clear documentation of agent capabilities
- **JSON Schema Compatibility**: Works with standard JSON Schema tools and validators

## 🆕 What's New: Persistent Vector Database

The agent now includes **persistent vector database storage**:
- **Disk Persistence**: FAISS index is saved to disk during initialization
- **Efficient Loading**: Index is loaded from disk on subsequent executions
- **No Re-indexing**: Eliminates the need to recreate embeddings on every execution
- **Faster Queries**: Subsequent queries are much faster as they use the cached index

## 📋 Schema Structure

The agent uses a flat JSON Schema structure in `config_schema` for the main execution interface:

```json
{
  "config_schema": {
    "name": "persistent_rag_agent",
    "description": "A RAG agent with document indexing and querying capabilities",
    "inputSchema": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "Question to ask about the indexed content",
          "minLength": 1,
          "maxLength": 1000
        }
      },
      "required": ["question"]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string"},
        "question": {"type": "string"},
        "website_url": {"type": "string"},
        "index_size": {"type": "integer"}
      },
      "required": ["answer", "question"]
    }
  }
}
```

## 🔄 Persistent Agent Lifecycle

This agent follows the persistent agent lifecycle with separate initialization and execution phases:

### 1. **Initialization Phase**
- **Method**: `initialize(config)`
- **Purpose**: Set up the agent with document indexing
- **Configuration**: Uses `initialization_config` for setup parameters
- **State**: Stores indexed content and configuration in persistent state
- **Vector Database**: Creates FAISS index and saves it to disk for persistence

### 2. **Execution Phase**
- **Method**: `execute(input_data)`
- **Purpose**: Process RAG queries against indexed content
- **Input**: Validated against `inputSchema` from `config_schema`
- **Output**: Validated against `outputSchema` from `config_schema`
- **Vector Database**: Loads pre-built FAISS index from disk (no re-indexing)

### 3. **Cleanup Phase**
- **Method**: `cleanup()`
- **Purpose**: Clean up resources when agent is no longer needed

## 🚀 Key Features

### 1. **Input Validation**
- Validates all input parameters against the `inputSchema`
- Ensures required fields are present
- Checks data types and constraints

### 2. **Output Validation**
- Validates agent outputs against the `outputSchema`
- Ensures consistent response format
- Catches unexpected output structures

### 3. **Runtime Safety**
- Prevents invalid inputs from reaching your agent
- Ensures outputs match expected format
- Better error handling and debugging

### 4. **Persistent State Management**
- Maintains indexed content across executions
- Stores configuration and metadata
- Platform handles persistence automatically

### 5. **Persistent Vector Database** 🆕
- **FAISS Index Persistence**: Saves vector embeddings to disk during initialization
- **Fast Loading**: Loads pre-built index on subsequent executions
- **Storage Efficiency**: Uses `/tmp/agenthub_persistent_rag/` for temporary storage
- **Agent Isolation**: Each agent instance gets its own storage directory
- **Fallback Recovery**: Automatically recreates index if disk storage fails

## 💾 Vector Database Storage

The agent stores the FAISS index and metadata in the following structure:

```
/tmp/agenthub_persistent_rag/
└── agent_{agent_id}/
    ├── faiss_index/          # FAISS index files
    └── documents.json        # Metadata and content
```

**Benefits:**
- **No Re-indexing**: Eliminates expensive embedding recreation on each execution
- **Faster Queries**: Subsequent queries use cached embeddings
- **Resource Efficiency**: Reduces API calls to embedding services
- **Persistent Across Executions**: Index survives container restarts (if storage persists)

## 📝 Usage Examples

### Initialization
```bash
# Initialize the agent with a website
agenthub hired initialize <hiring_id> --config '{
  "website_url": "https://example.com",
  "model_name": "gpt-4",
  "temperature": 0,
  "chunk_size": 1000,
  "agent_id": "my_rag_agent"
}'
```

**Note**: The `agent_id` parameter is optional but recommended for better storage isolation.

### Execution
```bash
# Execute a RAG query (uses cached index)
agenthub execute hiring <hiring_id> --input '{
  "question": "What is this website about?"
}'
```

### Expected Output
```json
{
  "answer": "This website is about artificial intelligence and machine learning technologies...",
  "question": "What is this website about?",
  "website_url": "https://example.com",
  "index_size": 150
}
```

## 🔧 Testing

### Local Testing
```bash
cd agenthub-sdk/templates/persistent_rag_agent

# Basic functionality test
python persistent_rag_agent.py

# Test persistence functionality specifically
python test_persistence.py

# Demo showing old vs new approach performance
python demo_persistence.py
```

The test scripts will demonstrate the persistence by:
1. **Basic Test** (`persistent_rag_agent.py`): Tests all agent methods
2. **Persistence Test** (`test_persistence.py`): Focuses on vector database persistence
3. **Performance Demo** (`demo_persistence.py`): Shows performance improvements

### CLI Validation
```bash
agenthub agent validate --directory agenthub-sdk/templates/persistent_rag_agent
```

### Platform Testing
```bash
# Submit the agent
agenthub agent publish --directory agenthub-sdk/templates/persistent_rag_agent

# Test initialization
agenthub hired initialize <hiring_id> --config '{"website_url": "https://example.com"}'

# Test execution
agenthub execute hiring <hiring_id> --input '{"question": "What is this about?"}'
```

## 📚 Schema Benefits

### For Agent Creators
- **Clear Documentation**: Input/output requirements are explicit
- **Better Testing**: Validate schemas before deployment
- **Error Prevention**: Catch issues early in development
- **Lifecycle Management**: Clear separation of initialization and execution
- **Performance Optimization**: Vector database persistence eliminates re-indexing overhead

### For Agent Users
- **Predictable Interface**: Know exactly what to send and expect
- **Better Integration**: Easy to integrate with other systems
- **Error Handling**: Clear error messages for invalid inputs
- **State Persistence**: No need to re-index documents for each query
- **Faster Queries**: Subsequent queries use cached embeddings

### For Platform
- **Quality Assurance**: Ensures agent reliability
- **API Consistency**: Standardized input/output formats
- **Monitoring**: Track validation success/failure rates
- **Resource Management**: Efficient handling of persistent state
- **Performance**: Reduced computational overhead for repeated queries

## 🔄 Migration from Old Format

If you have existing persistent agents, you can migrate them to JSON Schema format:

### Old Format (UI Forms)
```json
{
  "config_schema": {
    "execute": {
      "question": {
        "type": "string",
        "description": "Question to ask"
      }
    }
  }
}
```

### New JSON Schema Format
```json
{
  "config_schema": {
    "name": "my_agent",
    "inputSchema": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "Question to ask"
        }
      },
      "required": ["question"]
    },
    "outputSchema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string"}
      },
      "required": ["answer"]
    }
  }
}
```

## 🎯 Best Practices

1. **Be Specific**: Define detailed property descriptions
2. **Use Constraints**: Add `minLength`, `maxLength`, `enum` where appropriate
3. **Required Fields**: Only mark truly required fields as required
4. **Examples**: Include realistic input/output examples
5. **Validation**: Test your schemas with various inputs
6. **Lifecycle Separation**: Keep initialization and execution concerns separate
7. **State Management**: Use platform state management methods
8. **Vector Database Persistence**: Leverage disk storage for performance optimization
9. **Agent ID**: Use unique agent IDs for better storage isolation

## 🚨 Common Issues

### Schema Validation Errors
- Check that `inputSchema` and `outputSchema` are present
- Ensure all required fields are marked correctly
- Verify JSON Schema syntax is valid

### Runtime Validation Failures
- Input data doesn't match `inputSchema`
- Output data doesn't match `outputSchema`
- Missing required fields or wrong data types

### Persistent Agent Issues
- Agent not initialized before execution
- State not properly managed between calls
- Initialization configuration missing required fields

### Vector Database Issues
- **Storage Permissions**: Ensure `/tmp` directory is writable
- **Disk Space**: Check available disk space for index storage
- **Index Corruption**: Agent automatically falls back to recreation if loading fails
- **Container Restarts**: Index persistence depends on storage volume mounting

## 🔍 Performance Characteristics

### First Execution (Initialization)
- **Document Loading**: Downloads and processes website content
- **Text Chunking**: Splits content into manageable chunks
- **Embedding Creation**: Generates vector embeddings via OpenAI API
- **Index Building**: Creates FAISS vector index
- **Disk Storage**: Saves index and metadata to disk
- **Total Time**: ~10-30 seconds depending on content size

### Subsequent Executions
- **Index Loading**: Loads pre-built FAISS index from disk
- **Query Processing**: Direct vector similarity search
- **LLM Generation**: Generates answer using retrieved context
- **Total Time**: ~2-5 seconds (3-6x faster than first execution)

## 📖 Learn More

- [JSON Schema Specification](../AGENT_JSON_SCHEMA_SPECIFICATION.md)
- [AgentHub Documentation](../../../documentation/)
- [JSON Schema Reference](https://json-schema.org/)
- [Persistent Agent Guide](../../../documentation/PERSISTENT_AGENT_GUIDE.md)
- [FAISS Vector Database](https://github.com/facebookresearch/faiss)
- [LangChain Vector Stores](https://python.langchain.com/docs/modules/data_connection/vectorstores/) 