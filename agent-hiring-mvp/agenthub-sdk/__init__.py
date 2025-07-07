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

from .agent import Agent, AgentConfig, SimpleAgent, DataProcessingAgent, ChatAgent, ACPServerAgent
from .agent import create_simple_agent, create_data_agent, create_chat_agent, create_acp_server_agent
from .client import AgentHubClient

__version__ = "1.0.0"

__all__ = [
    # Agent Creation
    "Agent",
    "AgentConfig",
    "SimpleAgent", 
    "DataProcessingAgent",
    "ChatAgent",
    "ACPServerAgent",
    
    # Agent Factory Functions
    "create_simple_agent",
    "create_data_agent",
    "create_chat_agent",
    "create_acp_server_agent",
    
    # Client
    "AgentHubClient",
] 