# BeeAI Agent Creator SDK Guide

## Overview

The BeeAI Agent Creator SDK is built around the **Agent Communication Protocol (ACP)** and provides a comprehensive framework for creating AI agents that can be deployed on the BeeAI platform. The SDK offers both high-level abstractions (BeeAI Framework) and low-level ACP SDK components.

## SDK Architecture

### 1. **Core Components**

```python
# Primary SDK import
from acp_sdk import (
    Message, MessagePart, Metadata, Link, LinkType, 
    Annotations, Error, ErrorCode, Artifact
)
from acp_sdk.server import Server, Context
from acp_sdk.models.platform import PlatformUIAnnotation, PlatformUIType
```

### 2. **Two Development Approaches**

#### **Option A: BeeAI Framework (High-Level)**
- Built-in memory management
- Pre-built tools (web search, weather, Wikipedia)
- ReAct agent pattern
- Simplified configuration

#### **Option B: ACP SDK (Low-Level)**
- Direct control over agent behavior
- Custom streaming logic
- Integration with external frameworks
- Maximum flexibility

## Quick Start Examples

### **1. Simple Chat Agent (BeeAI Framework)**

```python
# pyproject.toml
[project]
name = "my-chat-agent"
version = "0.1.0"
dependencies = [
    "acp-sdk==1.0.0",
    "beeai-framework[duckduckgo,wikipedia]~=0.1.29",
]

[project.scripts]
server = "my_agent.agent:run"
```

```python
# src/my_agent/agent.py
import os
from collections.abc import AsyncGenerator
from acp_sdk import Message, Metadata, Annotations
from acp_sdk.server import Context, Server
from acp_sdk.models.platform import PlatformUIAnnotation, PlatformUIType

from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.search.duckduckgo import DuckDuckGoSearchTool

server = Server()

@server.agent(
    metadata=Metadata(
        annotations=Annotations(
            beeai_ui=PlatformUIAnnotation(
                ui_type=PlatformUIType.CHAT,
                user_greeting="How can I help you?",
                display_name="My Chat Agent",
            ),
        ),
        programming_language="Python",
        framework="BeeAI",
        license="Apache 2.0",
        documentation="A conversational AI agent with web search capabilities.",
        use_cases=["Q&A", "Research", "General conversation"],
        env=[
            {"name": "LLM_MODEL", "description": "Model to use"},
            {"name": "LLM_API_BASE", "description": "API endpoint"},
            {"name": "LLM_API_KEY", "description": "API key"},
        ],
    )
)
async def chat_agent(input: list[Message], context: Context) -> AsyncGenerator:
    """AI chat agent with web search capabilities."""
    
    # Configure LLM
    llm = ChatModel.from_name(
        f"openai:{os.getenv('LLM_MODEL', 'gpt-4')}"
    )
    
    # Configure tools
    tools = [DuckDuckGoSearchTool()]
    
    # Create agent
    agent = ReActAgent(llm=llm, tools=tools, memory=UnconstrainedMemory())
    
    # Load conversation history
    history = [message async for message in context.session.load_history()]
    
    # Process messages
    framework_messages = [to_framework_message(msg.role, str(msg)) 
                         for msg in history + input]
    await agent.memory.add_many(framework_messages)
    
    # Stream responses
    async for data, event in agent.run():
        if event.name == "partial_update":
            yield MessagePart(content=data.update.value)

def run():
    server.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()
```

### **2. Custom Agent (ACP SDK)**

```python
# pyproject.toml
[project]
name = "my-custom-agent"
version = "0.1.0"
dependencies = [
    "acp-sdk==1.0.0",
    "pydantic>=2.0.0",
]

[project.scripts]
server = "my_agent.agent:run"
```

```python
# src/my_agent/agent.py
import os
from typing import AsyncIterator
from acp_sdk import (
    Message, MessagePart, Metadata, Link, LinkType,
    Error, ErrorCode, Annotations
)
from acp_sdk.server import Server, Context
from acp_sdk.models.platform import PlatformUIAnnotation, PlatformUIType

server = Server()

@server.agent(
    metadata=Metadata(
        annotations=Annotations(
            beeai_ui=PlatformUIAnnotation(
                ui_type=PlatformUIType.HANDSOFF,
                user_greeting="What would you like me to process?",
                display_name="Custom Agent",
            ),
        ),
        programming_language="Python",
        framework="Custom",
        license="Apache 2.0",
        documentation="A custom agent that processes text input.",
        use_cases=["Text processing", "Data transformation"],
        env=[
            {"name": "API_KEY", "description": "External API key"},
        ],
    )
)
async def custom_agent(input: list[Message], context: Context) -> AsyncIterator:
    """Custom agent that processes text input."""
    
    try:
        # Get the latest message
        user_message = str(input[-1])
        
        # Process the message (your custom logic here)
        processed_text = await process_message(user_message)
        
        # Stream the response
        for chunk in processed_text.split():
            yield MessagePart(content=chunk + " ")
            
    except Exception as e:
        yield Error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Processing failed: {str(e)}"
        )

async def process_message(message: str) -> str:
    """Your custom processing logic here."""
    return f"Processed: {message.upper()}"

def run():
    server.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()
```

### **3. External Framework Integration**

```python
# Example: Integrating with existing Python libraries
import asyncio
import subprocess
from acp_sdk import Message, MessagePart, Artifact
from acp_sdk.server import Server, Context

server = Server()

@server.agent(metadata=Metadata(...))
async def external_tool_agent(input: list[Message], context: Context):
    """Agent that wraps external command-line tools."""
    
    user_request = str(input[-1])
    
    # Execute external tool
    process = await asyncio.create_subprocess_exec(
        "your-external-tool",
        "--input", user_request,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Stream output
    while True:
        chunk = await process.stdout.read(1024)
        if not chunk:
            break
        yield MessagePart(content=chunk.decode())
    
    await process.wait()
    
    # Return any generated files as artifacts
    yield Artifact(
        name="output.txt",
        content=b"Generated content",
        content_type="text/plain"
    )
```

## Key SDK Components

### **1. Message Handling**

```python
# Message structure
from acp_sdk import Message, MessagePart

# Input: List of messages from conversation
async def my_agent(input: list[Message], context: Context):
    # Get latest message
    latest_message = input[-1]
    
    # Extract content
    content = str(latest_message)
    
    # Access message parts
    for part in latest_message.parts:
        if part.content_type == "text/plain":
            text_content = part.content
        elif part.content_type == "application/json":
            json_content = part.content
```

### **2. Streaming Responses**

```python
# Different output types
async def streaming_agent(input: list[Message], context: Context):
    # Text response
    yield MessagePart(content="Hello, ")
    yield MessagePart(content="World!")
    
    # JSON response (for intermediate data)
    yield {"status": "processing", "progress": 50}
    
    # File artifacts
    yield Artifact(
        name="result.csv",
        content=b"name,value\nJohn,123",
        content_type="text/csv"
    )
    
    # Errors
    yield Error(
        code=ErrorCode.INVALID_INPUT,
        message="Invalid input provided"
    )
```

### **3. Context and Session Management**

```python
async def stateful_agent(input: list[Message], context: Context):
    # Load conversation history
    history = [msg async for msg in context.session.load_history()]
    
    # Access session ID
    session_id = context.session.id
    
    # Use context for stateful operations
    # (Memory is automatically managed by the platform)
```

### **4. UI Annotations**

```python
from acp_sdk.models.platform import (
    PlatformUIAnnotation, PlatformUIType, AgentToolInfo
)

# Different UI types
ui_annotations = {
    # Chat interface
    PlatformUIType.CHAT: PlatformUIAnnotation(
        ui_type=PlatformUIType.CHAT,
        user_greeting="How can I help you?",
        display_name="Chat Agent",
        tools=[
            AgentToolInfo(name="Web Search", description="Search the web"),
            AgentToolInfo(name="Calculator", description="Perform calculations"),
        ],
    ),
    
    # Hands-off processing
    PlatformUIType.HANDSOFF: PlatformUIAnnotation(
        ui_type=PlatformUIType.HANDSOFF,
        user_greeting="Describe your task.",
        display_name="Task Processor",
    ),
}
```

## Deployment Structure

### **1. Project Structure**

```
my-agent/
├── pyproject.toml          # Dependencies and scripts
├── uv.lock                 # Lock file
├── Dockerfile              # Container image
├── agent.yaml              # Agent metadata (optional)
├── src/
│   └── my_agent/
│       ├── __init__.py
│       └── agent.py        # Main agent implementation
└── tests/
    └── test_agent.py
```

### **2. Standard Dockerfile**

```dockerfile
FROM python:3.11-slim-bookworm
ARG RELEASE_VERSION="main"
COPY --from=ghcr.io/astral-sh/uv:0.6.16 /uv /bin/
WORKDIR /app
COPY . .
RUN uv sync --no-cache --locked --link-mode copy
ENV PRODUCTION_MODE=True \
    RELEASE_VERSION=${RELEASE_VERSION}
CMD ["uv", "run", "--no-sync", "server"]
```

### **3. Agent Configuration (agent.yaml)**

```yaml
manifestVersion: 1
name: "my-agent"
description: "A custom AI agent"
framework: "BeeAI"
license: "Apache 2.0"
languages: 
  - Python
avgRunTimeSeconds: 5.0
avgRunTokens: 1000

ui:
  type: chat
  userGreeting: "How can I help you?"

env:
  - name: LLM_MODEL
    required: false
    description: "Model to use"
  - name: LLM_API_KEY
    required: true
    description: "API key for model"

examples:
  cli:
    - command: 'beeai run my-agent "Hello, world!"'
      processingSteps:
        - "Agent receives message"
        - "Processes the request"
        - "Returns response"
```

## Advanced Features

### **1. Tool Integration**

```python
from beeai_framework.tools.tool import AnyTool
from beeai_framework.tools.search.duckduckgo import DuckDuckGoSearchTool
from beeai_framework.tools.weather.openmeteo import OpenMeteoTool

# Built-in tools
tools: list[AnyTool] = [
    DuckDuckGoSearchTool(),
    OpenMeteoTool(),
    WikipediaTool(),
]

# Custom tools
class CustomTool(AnyTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="A custom tool"
        )
    
    async def execute(self, input: str) -> str:
        # Your custom tool logic
        return f"Processed: {input}"
```

### **2. Memory Management**

```python
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.backend import UserMessage, AssistantMessage

# Memory is automatically managed by the platform
# But you can customize it with BeeAI Framework
memory = UnconstrainedMemory()

# Add messages to memory
await memory.add_many([
    UserMessage("Hello"),
    AssistantMessage("Hi there!")
])

# Memory is persisted across sessions automatically
```

### **3. Model Configuration**

```python
from beeai_framework.backend.chat import ChatModel, ChatModelParameters

# Configure different models
llm = ChatModel.from_name(
    f"openai:{os.getenv('LLM_MODEL', 'gpt-4')}",
    ChatModelParameters(
        temperature=0.7,
        max_tokens=1000,
        top_p=0.9,
    )
)
```

## Error Handling

```python
from acp_sdk import Error, ErrorCode

async def robust_agent(input: list[Message], context: Context):
    try:
        # Your agent logic here
        result = await process_input(input)
        yield MessagePart(content=result)
        
    except ValueError as e:
        yield Error(
            code=ErrorCode.INVALID_INPUT,
            message=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        yield Error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unexpected error: {str(e)}"
        )
```

## Testing Your Agent

```python
# tests/test_agent.py
import pytest
from acp_sdk import Message, MessagePart
from acp_sdk.server import Context, MemoryStore
from my_agent.agent import my_agent

@pytest.mark.asyncio
async def test_agent_response():
    # Create test context
    context = Context(
        session=MemoryStore().create_session(),
        request_id="test-123"
    )
    
    # Create test input
    input_messages = [
        Message(parts=[MessagePart(content="Hello, agent!")])
    ]
    
    # Test agent
    responses = []
    async for response in my_agent(input_messages, context):
        responses.append(response)
    
    # Verify responses
    assert len(responses) > 0
    assert isinstance(responses[0], MessagePart)
```

## Environment Configuration

```python
# Common environment variables
import os

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "your-api-key")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Platform Configuration
PLATFORM_URL = os.getenv("PLATFORM_URL", "http://localhost:8333")
```

## Deployment Commands

```bash
# Local development
uv run server

# Build container
docker build -t my-agent .

# Run container
docker run -p 8000:8000 \
  -e LLM_API_KEY=your-key \
  -e LLM_MODEL=gpt-4 \
  my-agent

# Deploy to BeeAI platform
beeai build my-agent
beeai run my-agent "Test message"
```

## Best Practices

### **1. Agent Design**
- Keep agents focused on specific tasks
- Use appropriate UI types (chat vs hands-off)
- Provide clear documentation and examples
- Handle errors gracefully

### **2. Performance**
- Use streaming for long-running operations
- Implement proper timeout handling
- Consider memory usage for large responses

### **3. Security**
- Validate all inputs
- Use environment variables for sensitive data
- Implement proper error handling without exposing internals

### **4. Testing**
- Write unit tests for agent logic
- Test with various input types
- Test error conditions
- Test streaming behavior

## Summary

The BeeAI Agent Creator SDK provides:

✅ **Two development approaches**: High-level BeeAI Framework or low-level ACP SDK
✅ **Streaming support**: Real-time response generation
✅ **Built-in tools**: Web search, weather, Wikipedia, and more
✅ **Flexible UI**: Chat interfaces or hands-off processing
✅ **Easy deployment**: Containerized agents with simple configuration
✅ **Session management**: Automatic conversation history and memory
✅ **Error handling**: Structured error responses
✅ **External integration**: Support for any Python library or external tool

The SDK is designed to be both powerful and approachable, allowing developers to create sophisticated AI agents with minimal boilerplate code while still providing the flexibility to implement custom behaviors when needed.