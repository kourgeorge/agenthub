#!/usr/bin/env python3
"""
AgentHub SDK - Agent Base Classes and Utilities
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base class for all agents."""
    
    def __init__(self):
        """Initialize the agent."""
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with input data and configuration.
        
        Args:
            input_data: Input data for execution
            config: Configuration data for the agent
            
        Returns:
            Dict with execution result
        """
        pass


class PersistentAgent(ABC):
    """
    Base class for persistent agents with state management.
    
    This class provides:
    - State management (_get_state/_set_state)
    - Lifecycle management (_is_initialized/_mark_initialized)
    - Abstract methods for agent implementation
    
    The platform handles all platform concerns (IDs, tracking, etc.).
    Agents focus only on business logic.
    """
    
    def __init__(self):
        self._state = {}
        self._initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the agent with configuration."""
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with input data."""
        pass
    
    def cleanup(self) -> Dict[str, Any]:
        """Clean up agent resources."""
        return {"status": "cleaned_up", "message": "Default cleanup completed"}
    
    def _get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent state."""
        return self._state.get(key, default)
    
    def _set_state(self, key: str, value: Any) -> None:
        """Set value in agent state."""
        self._state[key] = value
    
    def _is_initialized(self) -> bool:
        """Check if agent is initialized."""
        return self._initialized
    
    def _mark_initialized(self) -> None:
        """Mark agent as initialized."""
        self._initialized = True


class AgentConfig:
    """Configuration management for agents."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def get_lifecycle_method(self, phase: str) -> Optional[str]:
        """Get the method name for a lifecycle phase."""
        lifecycle = self.config.get("lifecycle", {})
        return lifecycle.get(phase)
    
    def get_agent_type(self) -> str:
        """Get the agent type."""
        return self.config.get("agent_type", "function")
    
    def get_agent_class(self) -> Optional[str]:
        """Get the agent class name for persistent agents."""
        return self.config.get("agent_class")
    
    def requires_initialization(self) -> bool:
        """Check if the agent requires initialization."""
        return self.config.get("requires_initialization", False)
    
    def get_entry_point(self) -> str:
        """Get the entry point file."""
        return self.config.get("entry_point", "agent.py")
    
    def validate(self) -> List[str]:
        """Validate the configuration and return list of errors."""
        return validate_agent_config(self.config)
    
    # Properties for backward compatibility
    @property
    def name(self) -> str:
        return self.config.get("name", "")
    
    @property
    def description(self) -> str:
        return self.config.get("description", "")
    
    @property
    def version(self) -> str:
        return self.config.get("version", "1.0.0")
    
    @property
    def author(self) -> str:
        return self.config.get("author", "")
    
    @property
    def email(self) -> str:
        return self.config.get("email", "")
    
    @property
    def entry_point(self) -> str:
        return self.config.get("entry_point", "agent.py")
    
    @property
    def requirements(self) -> List[str]:
        return self.config.get("requirements", [])
    
    @property
    def config_schema(self) -> Dict[str, Any]:
        return self.config.get("config_schema", {})
    
    @property
    def tags(self) -> List[str]:
        return self.config.get("tags", [])
    
    @property
    def category(self) -> str:
        return self.config.get("category", "general")
    
    @property
    def agent_type(self) -> str:
        return self.config.get("agent_type", "function")
    
    @property
    def pricing_model(self) -> str:
        return self.config.get("pricing_model", "free")
    
    @property
    def price_per_use(self) -> Optional[float]:
        return self.config.get("price_per_use")
    
    @property
    def subscription_price(self) -> Optional[float]:
        return self.config.get("subscription_price")
    
    @property
    def agent_class(self) -> Optional[str]:
        return self.config.get("agent_class")


def validate_agent_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate agent configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    required_fields = ["name", "description", "version", "entry_point"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    agent_type = config.get("agent_type")
    if agent_type not in ["function", "persistent"]:
        errors.append(f"Invalid agent_type: {agent_type}. Must be 'function' or 'persistent'")
    
    if agent_type == "persistent":
        lifecycle = config.get("lifecycle", {})
        required_lifecycle = ["initialize", "execute"]
        for phase in required_lifecycle:
            if phase not in lifecycle:
                errors.append(f"Persistent agent missing required lifecycle phase: {phase}")
    
    return errors


def load_agent_class(entry_point: str, agent_class: str = None) -> Any:
    """
    Load an agent class from an entry point file.
    
    Args:
        entry_point: Path to the entry point file
        agent_class: Name of the agent class (for persistent agents)
        
    Returns:
        The agent class or None if not found
    """
    try:
        import importlib.util
        import sys
        
        # Load the module
        spec = importlib.util.spec_from_file_location("agent_module", entry_point)
        module = importlib.util.module_from_spec(spec)
        sys.modules["agent_module"] = module
        spec.loader.exec_module(module)
        
        if agent_class:
            # Return the specific class
            return getattr(module, agent_class, None)
        else:
            # Return the module (for function agents)
            return module
            
    except Exception as e:
        logger.error(f"Error loading agent from {entry_point}: {e}")
        return None 