# Personal Assistant Agent

A comprehensive personal assistant agent built with LangGraph that provides a wide range of capabilities including web search, file management, academic research, and more.

## Features

### Core Capabilities
- **Web Search**: Search the web for current information using multiple search engines
- **Academic Research**: Access academic papers from arXiv, PubMed, Google Scholar, and Semantic Scholar
- **File Management**: Create, read, update, and delete files and directories
- **PDF Processing**: Load and extract text from PDF documents
- **Python Execution**: Safely execute Python code with restricted environment
- **Shell Commands**: Execute system commands (with safety restrictions)
- **Memory Storage**: Save and retrieve user-specific memories and preferences
- **Financial Data**: Get stock market information and financial data
- **Social Media**: Search Reddit for discussions and information

### Tools Available
- Wikipedia search
- arXiv academic papers
- PubMed medical research
- Google Scholar academic search
- Stack Exchange Q&A
- Google Serper web search
- Google Finance
- Reddit search
- File management operations
- PDF document processing
- Python code execution
- Shell command execution
- Memory storage and retrieval
- Semantic Scholar academic search

## Installation

1. Ensure you have the required dependencies installed:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export SERPER_API_KEY="your-serper-api-key"  # Optional, for enhanced web search
```

## Usage

### Basic Usage
```python
from personal_assistant_agent import main

# Simple request
result = main({
    "message": "What's the weather like today?",
    "user_id": "user123"
}, {})

print(result["response"])
```

### Advanced Usage
```python
from personal_assistant_agent import PersonalAssistantAgent
import asyncio

async def advanced_usage():
    agent = PersonalAssistantAgent(config={})
    await agent.initialize()
    
    result = await agent.process_request(
        user_input="Search for recent papers about machine learning",
        user_id="researcher123"
    )
    
    print(result["response"])

# Run the async function
asyncio.run(advanced_usage())
```

### Configuration Options
The agent accepts various configuration parameters:

- `message`: The user's request or question
- `user_id`: Unique identifier for the user (enables memory persistence)
- `system_prompt`: Custom system prompt for the assistant
- `enable_memory`: Whether to enable memory storage (default: true)
- `max_tokens`: Maximum response length (default: 2000)
- `temperature`: Response creativity (0.0-1.0, default: 0.1)

## Examples

### Web Search
```python
result = main({
    "message": "Search for the latest news about artificial intelligence",
    "user_id": "user123"
}, {})
```

### Academic Research
```python
result = main({
    "message": "Find recent papers about transformer models in NLP",
    "user_id": "researcher123"
}, {})
```

### File Operations
```python
result = main({
    "message": "Create a file called 'notes.txt' with the content 'Important meeting notes'",
    "user_id": "user123"
}, {})
```

### PDF Processing
```python
result = main({
    "message": "Load and summarize the PDF file 'document.pdf'",
    "user_id": "user123"
}, {})
```

### Memory Storage
```python
result = main({
    "message": "Remember that I prefer to work in the morning and my favorite color is blue",
    "user_id": "user123"
}, {})
```

## Architecture

The agent is built using LangGraph and follows a modular architecture:

1. **PersonalAssistantAgent**: Main agent class that orchestrates all functionality
2. **JSONFileStore**: Simple file-based storage for user memories
3. **Custom Tools**: Specialized tools for memory management, PDF processing, and Python execution
4. **LangGraph Integration**: Uses LangGraph's React agent pattern for tool execution

### Memory System
The agent maintains user-specific memories using a JSON-based file store. Memories are automatically retrieved and included in the context for each user interaction.

### Safety Features
- **Python Execution**: Restricted to safe built-in functions only
- **Shell Commands**: Limited to non-destructive operations
- **File Operations**: Basic file management with safety checks
- **Memory Isolation**: User-specific memory storage prevents cross-contamination

## Integration with AgentHub

This agent is designed to work seamlessly with the AgentHub platform:

1. **Standard Interface**: Follows the AgentHub agent interface pattern
2. **Configuration Schema**: Defined in `config.json` for platform integration
3. **Error Handling**: Comprehensive error handling and logging
4. **Resource Management**: Efficient resource usage and cleanup

## Development

### Adding New Tools
To add new tools to the agent:

1. Create a new tool class following the existing pattern
2. Add the tool to the `_initialize_tools` method in `PersonalAssistantAgent`
3. Update the requirements if needed
4. Test the integration

### Customizing the System Prompt
You can customize the assistant's behavior by modifying the system prompt in the `process_request` method or by passing a custom prompt in the configuration.

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required API keys are set in environment variables
2. **Import Errors**: Install all dependencies from `requirements.txt`
3. **Memory Issues**: Check file permissions for the memory storage file
4. **Tool Failures**: Some tools may require additional setup (e.g., Gmail requires OAuth setup)

### Debug Mode
Enable debug mode by setting `debug=True` in the `create_react_agent` call to get detailed execution logs.

## License

This agent is part of the AgentHub platform and follows the same licensing terms.

## Contributing

Contributions are welcome! Please follow the existing code patterns and ensure all tests pass before submitting a pull request. 