"""Database initialization for the Agent Hiring System."""

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_engine
from ..models import Base, Agent, AgentFile, User, Hiring, Execution

logger = logging.getLogger(__name__)


def init_database() -> None:
    """Initialize the database with tables and sample data."""
    engine = get_engine()
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create sample data
    logger.info("Creating sample data...")
    create_sample_data(engine)
    
    logger.info("Database initialization completed!")


def create_sample_data(engine) -> None:
    """Create sample data for development."""
    with Session(engine) as session:
        # Check if sample data already exists
        existing_agents = session.query(Agent).count()
        if existing_agents > 0:
            logger.info("Sample data already exists, skipping...")
            return
        
        # Create sample users
        sample_users = [
            User(
                username="admin",
                email="admin@agenthub.com",
                full_name="System Administrator",
                is_active=True,
                is_verified=True,
            ),
            User(
                username="creator1",
                email="creator1@example.com",
                full_name="Agent Creator",
                is_active=True,
                is_verified=True,
            ),
        ]
        
        for user in sample_users:
            session.add(user)
        session.commit()
        
        # Create sample agents with multiple files
        sample_agents = [
            Agent(
                name="Echo Agent",
                description="A simple agent that echoes back input messages with processing",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="echo_agent.py:main",
                requirements=[],
                tags=["echo", "simple", "demo"],
                category="utility",
                pricing_model="free",
                price_per_use=0.0,
                status="approved",
                is_public=True,
                code='''#!/usr/bin/env python3
"""
Simple Echo Agent
This agent simply echoes back the input message with some processing.
"""

from utils.helper import format_message

def main(input_data=None, config=None):
    """Main agent function."""
    # Use provided input_data or load from file as fallback
    if input_data is None:
        try:
            import json
            with open('input.json', 'r') as f:
                input_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            input_data = {}
    
    # Get input data from the environment
    message = input_data.get('message', 'Hello World!')
    prefix = input_data.get('prefix', 'Echo: ')
    
    # Process the message using helper function
    response = format_message(prefix, message)
    
    # Add some metadata
    result = {
        "response": response,
        "original_message": message,
        "timestamp": "2024-01-01T00:00:00Z",
        "agent_type": "echo"
    }
    
    # Print the result (this will be captured by the runtime)
    print(f"Agent Response: {result['response']}")
    print(f"Processing complete for message: {message}")
    
    # Return the result (this is what the runtime expects)
    return result

if __name__ == "__main__":
    main()''',
            ),
        ]
        
        for agent in sample_agents:
            session.add(agent)
        session.commit()
        
        # Create sample agent files for the Echo Agent
        echo_agent = session.query(Agent).filter(Agent.name == "Echo Agent").first()
        if echo_agent:
            # Main agent file
            main_file = AgentFile(
                agent_id=echo_agent.id,
                file_path="echo_agent.py",
                file_name="echo_agent.py",
                file_content='''#!/usr/bin/env python3
"""
Simple Echo Agent
This agent simply echoes back the input message with some processing.
"""

from utils.helper import format_message

def main(input_data=None, config=None):
    """Main agent function."""
    # Use provided input_data or load from file as fallback
    if input_data is None:
        try:
            import json
            with open('input.json', 'r') as f:
                input_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            input_data = {}
    
    # Get input data from the environment
    message = input_data.get('message', 'Hello World!')
    prefix = input_data.get('prefix', 'Echo: ')
    
    # Process the message using helper function
    response = format_message(prefix, message)
    
    # Add some metadata
    result = {
        "response": response,
        "original_message": message,
        "timestamp": "2024-01-01T00:00:00Z",
        "agent_type": "echo"
    }
    
    # Print the result (this will be captured by the runtime)
    print(f"Agent Response: {result['response']}")
    print(f"Processing complete for message: {message}")
    
    # Return the result (this is what the runtime expects)
    return result

if __name__ == "__main__":
    main()''',
                file_type=".py",
                file_size=1024,
                is_main_file="Y",
                is_executable="Y"
            )
            
            # Helper utility file
            helper_file = AgentFile(
                agent_id=echo_agent.id,
                file_path="utils/helper.py",
                file_name="helper.py",
                file_content='''#!/usr/bin/env python3
"""
Helper utilities for the Echo Agent.
"""

def format_message(prefix: str, message: str) -> str:
    """Format a message with a prefix."""
    return f"{prefix}{message}"

def validate_input(message: str) -> bool:
    """Validate input message."""
    return isinstance(message, str) and len(message.strip()) > 0
''',
                file_type=".py",
                file_size=256,
                is_main_file="N",
                is_executable="Y"
            )
            
            # Configuration file
            config_file = AgentFile(
                agent_id=echo_agent.id,
                file_path="config/settings.json",
                file_name="settings.json",
                file_content='''{
  "default_prefix": "Echo: ",
  "max_message_length": 1000,
  "enable_timestamp": true,
  "log_level": "info"
}''',
                file_type=".json",
                file_size=128,
                is_main_file="N",
                is_executable="N"
            )
            
            session.add_all([main_file, helper_file, config_file])
            session.commit()
            
            logger.info(f"Created sample agent files for Echo Agent (ID: {echo_agent.id})")
        
        logger.info("Sample data created successfully!")


def reset_database() -> None:
    """Reset the database (drop all tables and recreate)."""
    engine = get_engine()
    
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Recreating database...")
    init_database()
    
    logger.info("Database reset completed!")


if __name__ == "__main__":
    init_database() 