"""Database initialization for the Agent Hiring System."""

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_engine
from ..models import Base, Agent, User, Hiring, Execution

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
        
        # Create sample agents with actual code
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
    
    # Process the message
    response = f"{prefix}{message}"
    
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
            Agent(
                name="Calculator Agent",
                description="Performs mathematical operations on input data",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="calculator_agent.py:main",
                requirements=[],
                tags=["calculator", "math", "utility"],
                category="utility",
                pricing_model="free",
                price_per_use=0.0,
                status="approved",
                is_public=True,
                code='''#!/usr/bin/env python3
"""
Calculator Agent
This agent performs mathematical operations on input data.
"""

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
    
    # Get input data
    operation = input_data.get('operation', 'add')
    numbers = input_data.get('numbers', [1, 2])
    
    # Validate input
    if not isinstance(numbers, list) or len(numbers) < 2:
        print("Error: At least 2 numbers required")
        return {"error": "At least 2 numbers required"}
    
    # Perform calculation
    result = None
    if operation == 'add':
        result = sum(numbers)
    elif operation == 'multiply':
        result = 1
        for num in numbers:
            result *= num
    elif operation == 'subtract':
        result = numbers[0] - sum(numbers[1:])
    elif operation == 'divide':
        if 0 in numbers[1:]:
            print("Error: Division by zero")
            return {"error": "Division by zero"}
        result = numbers[0]
        for num in numbers[1:]:
            result /= num
    else:
        print(f"Error: Unknown operation '{operation}'")
        return {"error": f"Unknown operation '{operation}'"}
    
    # Format output
    print(f"Operation: {operation}")
    print(f"Numbers: {numbers}")
    print(f"Result: {result}")
    
    # Return structured result
    output = {
        "operation": operation,
        "numbers": numbers,
        "result": result,
        "agent_type": "calculator"
    }
    
    print(f"Calculation complete: {output}")
    return output

if __name__ == "__main__":
    main()''',
            ),
            Agent(
                name="Text Processor",
                description="Processes and analyzes text input with various operations",
                version="1.0.0",
                author="creator1",
                email="creator1@example.com",
                entry_point="text_processor_agent.py:main",
                requirements=[],
                tags=["text-processing", "analysis", "utility"],
                category="utility",
                pricing_model="free",
                price_per_use=0.0,
                status="approved",
                is_public=True,
                code='''#!/usr/bin/env python3
"""
Text Processor Agent
This agent processes and analyzes text input.
"""

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
    
    # Get input data
    text = input_data.get('text', 'Hello World!')
    operation = input_data.get('operation', 'analyze')
    
    # Process text based on operation
    if operation == 'analyze':
        # Basic text analysis
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.splitlines())
        
        analysis = {
            "text": text,
            "word_count": word_count,
            "character_count": char_count,
            "line_count": line_count,
            "average_word_length": char_count / word_count if word_count > 0 else 0
        }
        
        print(f"Text Analysis Results:")
        print(f"Word count: {analysis['word_count']}")
        print(f"Character count: {analysis['character_count']}")
        print(f"Line count: {analysis['line_count']}")
        print(f"Average word length: {analysis['average_word_length']:.2f}")
        
        result = analysis
        
    elif operation == 'uppercase':
        result = text.upper()
        print(f"Uppercase text: {result}")
        
    elif operation == 'lowercase':
        result = text.lower()
        print(f"Lowercase text: {result}")
        
    elif operation == 'reverse':
        result = text[::-1]
        print(f"Reversed text: {result}")
        
    elif operation == 'word_count':
        words = text.split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        print(f"Word frequency:")
        for word, count in word_freq.items():
            print(f"  '{word}': {count}")
        
        result = word_freq
            
    else:
        print(f"Error: Unknown operation '{operation}'")
        return {"error": f"Unknown operation '{operation}'"}
    
    print(f"Text processing complete for operation: {operation}")
    return result

if __name__ == "__main__":
    main()''',
            ),
        ]
        
        for agent in sample_agents:
            session.add(agent)
        session.commit()
        
        logger.info(f"Created {len(sample_users)} users and {len(sample_agents)} agents")


def reset_database() -> None:
    """Reset the database (drop all tables and recreate)."""
    engine = get_engine()
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Recreating database...")
    init_database()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database() 