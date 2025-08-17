# Persistent RAG Agent

This agent demonstrates the new **JSON Schema format** for AgentHub persistent agents. It shows how to define clear input and output schemas using the flat JSON Schema structure while maintaining the persistent agent lifecycle.

## 🆕 What's New: JSON Schema Format

The JSON Schema format provides:
- **Clear Input/Output Contracts**: Define exactly what your agent expects and returns
- **Runtime Validation**: Automatic validation of inputs and outputs during execution
- **Better Developer Experience**: Clear documentation of agent capabilities
- **JSON Schema Compatibility**: Works with standard JSON Schema tools and validators

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

### 2. **Execution Phase**
- **Method**: `execute(input_data)`
- **Purpose**: Process RAG queries against indexed content
- **Input**: Validated against `inputSchema` from `config_schema`
- **Output**: Validated against `outputSchema` from `config_schema`

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

## 📝 Usage Examples

### Initialization
```bash
# Initialize the agent with a website
agenthub hired initialize <hiring_id> --config '{
  "website_url": "https://example.com",
  "model_name": "gpt-4",
  "temperature": 0,
  "chunk_size": 1000
}'
```

### Execution
```bash
# Execute a RAG query
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
python persistent_rag_agent.py
```

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

### For Agent Users
- **Predictable Interface**: Know exactly what to send and expect
- **Better Integration**: Easy to integrate with other systems
- **Error Handling**: Clear error messages for invalid inputs
- **State Persistence**: No need to re-index documents for each query

### For Platform
- **Quality Assurance**: Ensures agent reliability
- **API Consistency**: Standardized input/output formats
- **Monitoring**: Track validation success/failure rates
- **Resource Management**: Efficient handling of persistent state

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

## 📖 Learn More

- [JSON Schema Specification](../AGENT_JSON_SCHEMA_SPECIFICATION.md)
- [AgentHub Documentation](../../../documentation/)
- [JSON Schema Reference](https://json-schema.org/)
- [Persistent Agent Guide](../../../documentation/PERSISTENT_AGENT_GUIDE.md) 