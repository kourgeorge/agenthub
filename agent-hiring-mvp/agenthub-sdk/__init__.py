"""
AgentHub SDK - Complete SDK for Agent Creation and Hiring

This SDK provides tools for both agent creators and users:
- Agent creators can build, test, and submit agents
- Users can hire agents and execute tasks
"""

from .agent import Agent, AgentConfig, SimpleAgent, DataProcessingAgent, ChatAgent
from .client import AgentHubClient
from .hiring import HiringManager
from .execution import ExecutionManager
from .templates import get_template, list_templates, create_agent_from_template

__version__ = "1.0.0"

__all__ = [
    # Agent Creation
    "Agent",
    "AgentConfig",
    "SimpleAgent", 
    "DataProcessingAgent",
    "ChatAgent",
    
    # Client
    "AgentHubClient",
    
    # Hiring & Execution
    "HiringManager",
    "ExecutionManager",
    
    # Templates
    "get_template",
    "list_templates", 
    "create_agent_from_template",
] 