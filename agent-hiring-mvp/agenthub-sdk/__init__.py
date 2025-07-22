"""
AgentHub SDK - Complete SDK for Agent Creation and Hiring

This SDK provides tools for both agent creators and users:
- Agent creators can build, test, and submit agents
- Users can hire agents and execute tasks

CLI usage:
    # Initialize a new agent
    agenthub agent init my-agent --type simple
    
    # Validate an agent
    agenthub agent validate
    
    # Test an agent locally
    agenthub agent test
    
    # Publish an agent
    agenthub agent publish
    
    # List agents
    agenthub agent list
    
    # Configure CLI
    agenthub config --author "Your Name" --email "your@email.com"
"""

from .agent import Agent, PersistentAgent, AgentConfig, validate_agent_config, load_agent_class
from .client import AgentHubClient
from .cli import cli

__version__ = "1.0.0"

__all__ = [
    # Agent Base Classes
    "Agent",
    "PersistentAgent",
    
    # Configuration
    "AgentConfig",
    "validate_agent_config",
    "load_agent_class",
    
    # Client
    "AgentHubClient",
    
    # CLI
    "cli",
] 