"""Agent base class for the Creator SDK."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    
    # Basic Information
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    email: str = ""
    
    # Agent Configuration
    entry_point: str = "main.py:AgentClass"
    requirements: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    # Pricing
    pricing_model: Optional[str] = None  # "free", "per_use", "subscription"
    price_per_use: Optional[float] = None
    monthly_price: Optional[float] = None
    
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
        }


class Agent(ABC):
    """Base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"agent.{config.name}")
    
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
    
    def validate_config(self) -> List[str]:
        """Validate the agent configuration."""
        errors = []
        
        if not self.config.name:
            errors.append("Agent name is required")
        
        if not self.config.description:
            errors.append("Agent description is required")
        
        if not self.config.author:
            errors.append("Agent author is required")
        
        if not self.config.email:
            errors.append("Agent email is required")
        
        if not self.config.entry_point:
            errors.append("Agent entry point is required")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "config": self.config.to_dict(),
            "type": self.__class__.__name__,
        }


class SimpleAgent(Agent):
    """Simple agent implementation for basic use cases."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.context: Dict[str, Any] = {}
    
    async def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the agent."""
        self.context = context
        self.logger.info(f"Initialized agent: {self.config.name}")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message (to be overridden by subclasses)."""
        return {
            "status": "success",
            "message": "Message processed successfully",
            "data": message,
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.context.clear()
        self.logger.info(f"Cleaned up agent: {self.config.name}")


class DataProcessingAgent(SimpleAgent):
    """Agent for data processing tasks."""
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process data processing message."""
        data = message.get("data", {})
        operation = message.get("operation", "process")
        
        if operation == "process":
            # Simple data processing example
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


class ChatAgent(SimpleAgent):
    """Agent for chat/conversation tasks."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.conversation_history: List[Dict[str, Any]] = []
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chat message."""
        user_message = message.get("message", "")
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Generate response (to be overridden by subclasses)
        response = await self._generate_response(user_message)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return {
            "status": "success",
            "response": response,
            "conversation_id": message.get("conversation_id"),
        }
    
    async def _generate_response(self, message: str) -> str:
        """Generate a response to the user message (to be overridden)."""
        return f"Echo: {message}"
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.conversation_history.clear()
        await super().cleanup() 