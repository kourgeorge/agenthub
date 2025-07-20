"""
Agent base classes and configuration for the AgentHub SDK.
Provides tools for creating different types of agents.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    email: str = ""
    entry_point: str = ""
    requirements: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    pricing_model: str = "free"  # free, per_use, monthly
    price_per_use: Optional[float] = None
    monthly_price: Optional[float] = None
    max_execution_time: int = 30  # seconds
    memory_limit: str = "100MB"
    # ACP Server specific fields
    agent_type: str = "function"  # function, acp_server
    acp_manifest: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "email": self.email,
            "entry_point": self.entry_point,
            "requirements": self.requirements,
            "config_schema": self.config_schema,
            "tags": self.tags,
            "category": self.category,
            "pricing_model": self.pricing_model,
            "price_per_use": self.price_per_use,
            "monthly_price": self.monthly_price,
            "max_execution_time": self.max_execution_time,
            "memory_limit": self.memory_limit,
            "agent_type": self.agent_type,
            "acp_manifest": self.acp_manifest,
        }
    
    def validate(self) -> List[str]:
        """Validate the configuration."""
        errors = []
        
        if not self.name:
            errors.append("Agent name is required")
        
        if not self.description:
            errors.append("Agent description is required")
        
        if not self.author:
            errors.append("Agent author is required")
        
        if not self.email:
            errors.append("Agent email is required")
        
        if not self.entry_point:
            errors.append("Agent entry point is required")
        
        if self.pricing_model not in ["free", "per_use", "monthly"]:
            errors.append("Invalid pricing model")
        
        if self.pricing_model == "per_use" and self.price_per_use is None:
            errors.append("Price per use is required for per_use pricing model")
        
        if self.pricing_model == "monthly" and self.monthly_price is None:
            errors.append("Monthly price is required for monthly pricing model")
        
        # Validate agent type
        if self.agent_type not in ["function", "acp_server"]:
            errors.append("Invalid agent type. Must be 'function' or 'acp_server'")
        
        # Validate ACP server specific requirements
        if self.agent_type == "acp_server":
            if not self.acp_manifest:
                errors.append("ACP manifest is required for acp_server agents")
            else:
                # Validate required ACP manifest fields
                required_acp_fields = ["acp_version", "endpoints", "capabilities", "deployment"]
                for field in required_acp_fields:
                    if field not in self.acp_manifest:
                        errors.append(f"ACP manifest missing required field: {field}")
        
        # Validate config_schema if present
        if self.config_schema:
            schema_errors = self._validate_config_schema()
            errors.extend(schema_errors)
        
        return errors
    
    def _validate_config_schema(self) -> List[str]:
        """Validate the config_schema parameter types and formats."""
        errors = []
        
        if not isinstance(self.config_schema, dict):
            errors.append("config_schema must be a dictionary")
            return errors
        
        # Valid parameter types
        valid_types = {
            "string", "number", "integer", "float", "boolean", 
            "choice", "select", "textarea", "array", "object"
        }
        
        # Valid choice/select formats
        valid_choice_formats = {"options", "choices"}
        
        for param_name, param_config in self.config_schema.items():
            # Validate parameter name
            if not isinstance(param_name, str) or not param_name.strip():
                errors.append(f"Parameter name must be a non-empty string, got: {param_name}")
                continue
            
            # Validate parameter config is a dictionary
            if not isinstance(param_config, dict):
                errors.append(f"Parameter '{param_name}' config must be a dictionary")
                continue
            
            # Validate required fields
            if "type" not in param_config:
                errors.append(f"Parameter '{param_name}' missing required 'type' field")
                continue
            
            param_type = param_config["type"]
            
            # Validate parameter type
            if param_type not in valid_types:
                errors.append(f"Parameter '{param_name}' has invalid type '{param_type}'. Valid types: {', '.join(sorted(valid_types))}")
                continue
            
            # Validate type-specific requirements
            if param_type == "choice":
                # Choice parameters must have either 'options' or 'choices' array
                has_options = "options" in param_config
                has_choices = "choices" in param_config
                
                if not has_options and not has_choices:
                    errors.append(f"Parameter '{param_name}' (choice type) must have either 'options' or 'choices' array")
                elif has_options and has_choices:
                    errors.append(f"Parameter '{param_name}' (choice type) cannot have both 'options' and 'choices' arrays")
                elif has_options:
                    # Validate options format
                    options = param_config["options"]
                    if not isinstance(options, list):
                        errors.append(f"Parameter '{param_name}' options must be a list")
                    else:
                        for i, option in enumerate(options):
                            if not isinstance(option, dict):
                                errors.append(f"Parameter '{param_name}' option {i} must be a dictionary")
                            elif "value" not in option or "label" not in option:
                                errors.append(f"Parameter '{param_name}' option {i} must have 'value' and 'label' fields")
                elif has_choices:
                    # Validate choices format (legacy format)
                    choices = param_config["choices"]
                    if not isinstance(choices, list):
                        errors.append(f"Parameter '{param_name}' choices must be a list")
                    elif not all(isinstance(choice, str) for choice in choices):
                        errors.append(f"Parameter '{param_name}' choices must be a list of strings")
            
            elif param_type == "select":
                # Select parameters must have 'options' array
                if "options" not in param_config:
                    errors.append(f"Parameter '{param_name}' (select type) must have 'options' array")
                else:
                    options = param_config["options"]
                    if not isinstance(options, list):
                        errors.append(f"Parameter '{param_name}' options must be a list")
                    else:
                        for i, option in enumerate(options):
                            if not isinstance(option, dict):
                                errors.append(f"Parameter '{param_name}' option {i} must be a dictionary")
                            elif "value" not in option or "label" not in option:
                                errors.append(f"Parameter '{param_name}' option {i} must have 'value' and 'label' fields")
            
            elif param_type in ["number", "integer", "float"]:
                # Numeric parameters can have min/max constraints
                for constraint in ["min", "max", "minimum", "maximum"]:
                    if constraint in param_config:
                        value = param_config[constraint]
                        if not isinstance(value, (int, float)):
                            errors.append(f"Parameter '{param_name}' {constraint} must be a number")
            
            elif param_type == "string":
                # String parameters can have pattern validation
                if "pattern" in param_config:
                    pattern = param_config["pattern"]
                    if not isinstance(pattern, str):
                        errors.append(f"Parameter '{param_name}' pattern must be a string")
                    else:
                        try:
                            import re
                            re.compile(pattern)
                        except re.error:
                            errors.append(f"Parameter '{param_name}' pattern is not a valid regex")
            
            # Validate default value type matches parameter type
            if "default" in param_config:
                default_value = param_config["default"]
                if param_type == "boolean" and not isinstance(default_value, bool):
                    errors.append(f"Parameter '{param_name}' default value must be boolean for boolean type")
                elif param_type in ["number", "integer", "float"] and not isinstance(default_value, (int, float)):
                    errors.append(f"Parameter '{param_name}' default value must be a number for {param_type} type")
                elif param_type == "string" and not isinstance(default_value, str):
                    errors.append(f"Parameter '{param_name}' default value must be a string for string type")
                elif param_type == "choice" and "options" in param_config:
                    # Check if default value exists in options
                    valid_values = [opt["value"] for opt in param_config["options"]]
                    if default_value not in valid_values:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in options: {valid_values}")
                elif param_type == "choice" and "choices" in param_config:
                    # Check if default value exists in choices (legacy format)
                    if default_value not in param_config["choices"]:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in choices: {param_config['choices']}")
                elif param_type == "select":
                    # Check if default value exists in options
                    valid_values = [opt["value"] for opt in param_config["options"]]
                    if default_value not in valid_values:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in options: {valid_values}")
        
        return errors


class Agent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"agent.{config.name}")
        
        # Validate config
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid agent configuration: {'; '.join(errors)}")
    
    @abstractmethod
    async def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the agent with context."""
        pass
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources when the agent is done."""
        pass
    
    def get_config(self) -> AgentConfig:
        """Get the agent configuration."""
        return self.config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "config": self.config.to_dict(),
            "type": self.__class__.__name__,
        }
    
    def generate_code(self) -> str:
        """Generate the agent code as a string."""
        raise NotImplementedError("Subclasses must implement generate_code()")
    
    def save_to_directory(self, directory: str) -> None:
        """Save the agent code to a directory."""
        directory_path = Path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)
        
        # Generate and save main agent file
        code = self.generate_code()
        main_file = directory_path / f"{self.config.name.lower().replace(' ', '_')}.py"
        with open(main_file, 'w') as f:
            f.write(code)
        
        # Save requirements.txt
        if self.config.requirements:
            requirements_file = directory_path / "requirements.txt"
            with open(requirements_file, 'w') as f:
                f.write('\n'.join(self.config.requirements))
        
        # Save README.md
        readme_content = self._generate_readme()
        readme_file = directory_path / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        # Save config.json
        config_file = directory_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
    
    def _generate_readme(self) -> str:
        """Generate a README file for the agent."""
        return f"""# {self.config.name}

{self.config.description}

## Configuration

- **Version**: {self.config.version}
- **Author**: {self.config.author}
- **Category**: {self.config.category}
- **Pricing**: {self.config.pricing_model}
- **Entry Point**: {self.config.entry_point}

## Requirements

{chr(10).join(f'- {req}' for req in self.config.requirements) if self.config.requirements else 'No external requirements'}

## Usage

This agent can be executed through the AgentHub platform.

## Tags

{', '.join(self.config.tags)}
"""


class SimpleAgent(Agent):
    """Simple agent implementation for basic tasks."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.context: Dict[str, Any] = {}
    
    async def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the agent with context."""
        self.context = context
        self.logger.info(f"Initialized {self.config.name}")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response."""
        # Default implementation - subclasses should override
        return {
            "status": "success",
            "message": f"Processed by {self.config.name}",
            "data": message,
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.context.clear()
        self.logger.info(f"Cleaned up {self.config.name}")
    
    def generate_code(self) -> str:
        """Generate the agent code."""
        return f'''#!/usr/bin/env python3
"""
{self.config.name}
{self.config.description}
"""

def main():
    """Main agent function."""
    # Get input data
    input_data = globals().get('input_data', {{}})
    
    # Process the input
    message = input_data.get('message', 'Hello World!')
    
    # Your agent logic here
    result = f"Processed: {{message}}"
    
    # Print result (will be captured by runtime)
    print(f"Result: {{result}}")
    
    # Return structured output
    output = {{
        "status": "success",
        "result": result,
        "agent": "{self.config.name}",
        "version": "{self.config.version}"
    }}
    
    print(f"Agent output: {{output}}")

if __name__ == "__main__":
    main()
'''


class DataProcessingAgent(SimpleAgent):
    """Agent for data processing tasks."""
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process data processing message."""
        data = message.get("data", {})
        operation = message.get("operation", "process")
        
        if operation == "process":
            processed_data = self._process_data(data)
            return {
                "status": "success",
                "result": processed_data,
                "operation": operation,
            }
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
            }
    
    def _process_data(self, data: Any) -> Any:
        """Process the data (to be overridden by subclasses)."""
        return data
    
    def generate_code(self) -> str:
        """Generate data processing agent code."""
        return f'''#!/usr/bin/env python3
"""
{self.config.name} - Data Processing Agent
{self.config.description}
"""

def main():
    """Main agent function."""
    # Get input data
    input_data = globals().get('input_data', {{}})
    
    # Extract parameters
    data = input_data.get('data', [])
    operation = input_data.get('operation', 'process')
    
    # Process data based on operation
    if operation == 'process':
        result = process_data(data)
    elif operation == 'analyze':
        result = analyze_data(data)
    elif operation == 'transform':
        result = transform_data(data)
    else:
        result = {{"error": f"Unknown operation: {{operation}}"}}
    
    # Print result
    print(f"Data processing result: {{result}}")
    
    # Return structured output
    output = {{
        "status": "success",
        "operation": operation,
        "result": result,
        "agent": "{self.config.name}",
        "version": "{self.config.version}"
    }}
    
    print(f"Agent output: {{output}}")

def process_data(data):
    """Process the data."""
    # Override this function in your agent
    return {{"processed": data, "count": len(data) if isinstance(data, list) else 1}}

def analyze_data(data):
    """Analyze the data."""
    # Override this function in your agent
    return {{"analysis": "Basic analysis", "data": data}}

def transform_data(data):
    """Transform the data."""
    # Override this function in your agent
    return {{"transformed": data}}

if __name__ == "__main__":
    main()
'''


class ChatAgent(SimpleAgent):
    """Agent for chat and conversation tasks."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.conversation_history: List[Dict[str, Any]] = []
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chat message."""
        user_message = message.get("message", "")
        context = message.get("context", {})
        
        # Add to conversation history
        self.conversation_history.append({
            "user": user_message,
            "timestamp": "now"
        })
        
        # Generate response
        response = self._generate_response(user_message, context)
        
        # Add response to history
        self.conversation_history.append({
            "agent": response,
            "timestamp": "now"
        })
        
        return {
            "status": "success",
            "response": response,
            "conversation_length": len(self.conversation_history),
        }
    
    def _generate_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate a response to the user message."""
        # Default implementation - subclasses should override
        return f"Hello! I'm {self.config.name}. You said: {message}"
    
    def generate_code(self) -> str:
        """Generate chat agent code."""
        return f'''#!/usr/bin/env python3
"""
{self.config.name} - Chat Agent
{self.config.description}
"""

def main():
    """Main agent function."""
    # Get input data
    input_data = globals().get('input_data', {{}})
    
    # Extract message
    message = input_data.get('message', 'Hello!')
    context = input_data.get('context', {{}})
    
    # Generate response
    response = generate_response(message, context)
    
    # Print result
    print(f"Chat response: {{response}}")
    
    # Return structured output
    output = {{
        "status": "success",
        "response": response,
        "agent": "{self.config.name}",
        "version": "{self.config.version}"
    }}
    
    print(f"Agent output: {{output}}")

def generate_response(message, context):
    """Generate a response to the user message."""
    # Override this function in your agent
    return f"Hello! I'm {self.config.name}. You said: {{message}}"

if __name__ == "__main__":
    main()
'''


# Utility functions for creating agents
def create_simple_agent(
    name: str,
    description: str,
    author: str,
    email: str,
    **kwargs
) -> SimpleAgent:
    """Create a simple agent with basic configuration."""
    config = AgentConfig(
        name=name,
        description=description,
        author=author,
        email=email,
        entry_point=f"{name.lower().replace(' ', '_')}.py:main",
        **kwargs
    )
    return SimpleAgent(config)


def create_data_agent(
    name: str,
    description: str,
    author: str,
    email: str,
    **kwargs
) -> DataProcessingAgent:
    """Create a data processing agent."""
    config = AgentConfig(
        name=name,
        description=description,
        author=author,
        email=email,
        entry_point=f"{name.lower().replace(' ', '_')}.py:main",
        category="data-processing",
        **kwargs
    )
    return DataProcessingAgent(config)


def create_chat_agent(
    name: str,
    description: str,
    author: str,
    email: str,
    **kwargs
) -> ChatAgent:
    """Create a chat agent."""
    config = AgentConfig(
        name=name,
        description=description,
        author=author,
        email=email,
        entry_point=f"{name.lower().replace(' ', '_')}.py:main",
        category="chat",
        **kwargs
    )
    return ChatAgent(config)


class ACPServerAgent(Agent):
    """ACP Server agent implementation for microservice-based agents."""
    
    def __init__(self, config: AgentConfig):
        # Ensure this is an ACP server agent
        if config.agent_type != "acp_server":
            config.agent_type = "acp_server"
        
        super().__init__(config)
        self.context: Dict[str, Any] = {}
    
    async def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the ACP server agent with context."""
        self.context = context
        self.logger.info(f"Initialized ACP server agent {self.config.name}")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message through ACP protocol."""
        # ACP server agents handle messages through their server endpoints
        return {
            "status": "success",
            "message": "ACP server agent processes messages through server endpoints",
            "agent": self.config.name,
            "version": self.config.version,
            "endpoints": self.config.acp_manifest.get("endpoints", {}) if self.config.acp_manifest else {}
        }
    
    async def cleanup(self) -> None:
        """Clean up ACP server resources."""
        self.logger.info(f"Cleaning up ACP server agent {self.config.name}")
    
    def generate_code(self) -> str:
        """Generate ACP server agent code."""
        return f'''#!/usr/bin/env python3
"""
{self.config.name} - ACP Server Agent
{self.config.description}
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock ACP SDK classes (replace with real ACP SDK imports)
class MessageType:
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"

class Message:
    def __init__(self, type: str, content: Any):
        self.type = type
        self.content = content

class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters

class ToolCall:
    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.name = name
        self.arguments = arguments
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(data.get("name", ""), data.get("arguments", {{}}))

class ToolResult:
    def __init__(self, success: bool, content: Any):
        self.success = success
        self.content = content
    
    def to_dict(self):
        return {{"success": self.success, "content": self.content}}

class Context:
    def __init__(self):
        self.data = {{}}

class Agent:
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description


class {self.config.name.replace(' ', '').replace('-', '_')}(Agent):
    """
    ACP Server Agent - {self.config.description}
    """
    
    def __init__(self):
        super().__init__(
            name="{self.config.name}",
            version="{self.config.version}",
            description="{self.config.description}"
        )
        self.context = Context()
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        logger.info(f"Initializing {{self.name}} v{{self.version}}")
        
        # Add your initialization logic here
        pass
        
    async def process_message(self, message: Message) -> List[Message]:
        """Process incoming messages."""
        logger.info(f"Processing message: {{message.type}}")
        
        try:
            if message.type == MessageType.TEXT:
                return await self._handle_text_message(message)
            elif message.type == MessageType.TOOL_CALL:
                return await self._handle_tool_call(message)
            else:
                return [Message(
                    type=MessageType.TEXT,
                    content=f"Unsupported message type: {{message.type}}"
                )]
                
        except Exception as e:
            logger.error(f"Error processing message: {{e}}")
            return [Message(
                type=MessageType.ERROR,
                content=f"Error: {{str(e)}}"
            )]
    
    async def _handle_text_message(self, message: Message) -> List[Message]:
        """Handle text messages."""
        text = message.content
        
        # Your text processing logic here
        response = f"Processed: {{text}}"
        
        return [Message(
            type=MessageType.TEXT,
            content=response
        )]
    
    async def _handle_tool_call(self, message: Message) -> List[Message]:
        """Handle tool calls."""
        tool_call = ToolCall.from_dict(message.content)
        
        # Process the tool call
        result = await self._execute_tool(tool_call)
        
        return [Message(
            type=MessageType.TOOL_RESULT,
            content=result.to_dict()
        )]
    
    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call."""
        try:
            if tool_call.name == "get_info":
                return ToolResult(
                    success=True,
                    content={{
                        "agent": self.name,
                        "version": self.version,
                        "description": self.description
                    }}
                )
            else:
                return ToolResult(
                    success=False,
                    content=f"Unknown tool: {{tool_call.name}}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Tool execution error: {{str(e)}}"
            )
    
    def get_available_tools(self) -> List[Tool]:
        """Get list of available tools."""
        return [
            Tool(
                name="get_info",
                description="Get agent information",
                parameters={{
                    "type": "object",
                    "properties": {{}},
                    "required": []
                }}
            )
        ]


async def main():
    """Main entry point for the ACP server."""
    agent = {self.config.name.replace(' ', '').replace('-', '_')}()
    
    # Initialize the agent
    await agent.initialize()
    
    print(f"🚀 ACP Server Agent: {{agent.name}}")
    print(f"Version: {{agent.version}}")
    print(f"Description: {{agent.description}}")
    print("=" * 50)
    
    # For testing, simulate processing a message
    test_message = Message(MessageType.TEXT, "Hello from ACP client")
    responses = await agent.process_message(test_message)
    
    print("Test Response:")
    for response in responses:
        print(f"- {{response.type}}: {{response.content}}")
    
    print("\\n✅ ACP server agent running successfully!")
    
    # In production, start the actual ACP server here
    # server = create_server(agent)
    # port = int(os.environ.get("ACP_PORT", 8080))
    # await server.run(port=port)


if __name__ == "__main__":
    asyncio.run(main())
'''


def create_acp_server_agent(
    name: str,
    description: str,
    author: str,
    email: str,
    acp_manifest: Dict[str, Any],
    **kwargs
) -> ACPServerAgent:
    """Create an ACP server agent with the given configuration."""
    config = AgentConfig(
        name=name,
        description=description,
        author=author,
        email=email,
        agent_type="acp_server",
        acp_manifest=acp_manifest,
        entry_point=f"{name.lower().replace(' ', '_')}.py",
        **kwargs
    )
    
    return ACPServerAgent(config) 