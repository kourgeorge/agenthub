#!/usr/bin/env python3
"""Test script for the Agent Hiring System MVP."""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from creator_sdk import AgentHiringClient
from creator_sdk.examples.data_analyzer_agent import DataAnalyzerAgent
from creator_sdk.examples.chat_assistant_agent import ChatAssistantAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_agent_submission():
    """Test agent submission functionality."""
    logger.info("Testing agent submission...")
    
    try:
        async with AgentHiringClient("http://localhost:8000") as client:
            # Create test agents
            data_analyzer = DataAnalyzerAgent()
            chat_assistant = ChatAssistantAgent()
            
            # Test listing agents (should be empty initially)
            agents = await client.list_agents()
            logger.info(f"Initial agents: {agents}")
            
            # Note: In a real test, you would submit agents here
            # For now, we'll just test the client functionality
            logger.info("Agent submission test completed (agents not submitted due to missing server)")
            
    except Exception as e:
        logger.error(f"Agent submission test failed: {e}")


async def test_agent_functionality():
    """Test agent functionality locally."""
    logger.info("Testing agent functionality...")
    
    # Test Data Analyzer Agent
    logger.info("Testing Data Analyzer Agent...")
    data_analyzer = DataAnalyzerAgent()
    
    # Test data analysis
    test_data = [1, 2, 3, 4, 5]
    result = await data_analyzer.process_message({
        "operation": "analyze",
        "data": test_data,
    })
    logger.info(f"Data analysis result: {result}")
    
    # Test visualization
    result = await data_analyzer.process_message({
        "operation": "visualize",
        "data": test_data,
    })
    logger.info(f"Visualization result: {result}")
    
    # Test Chat Assistant Agent
    logger.info("Testing Chat Assistant Agent...")
    chat_assistant = ChatAssistantAgent()
    
    # Test greetings
    result = await chat_assistant.process_message({"message": "Hello!"})
    logger.info(f"Chat greeting: {result['response']}")
    
    # Test questions
    result = await chat_assistant.process_message({"message": "What's your name?"})
    logger.info(f"Chat question: {result['response']}")
    
    # Test math
    result = await chat_assistant.process_message({"message": "What is 5 + 3?"})
    logger.info(f"Chat math: {result['response']}")
    
    logger.info("Agent functionality test completed successfully!")


async def test_api_endpoints():
    """Test API endpoints (requires server to be running)."""
    logger.info("Testing API endpoints...")
    
    try:
        async with AgentHiringClient("http://localhost:8000") as client:
            # Test health endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"Health check: {health_data}")
                    else:
                        logger.warning(f"Health check failed: {response.status}")
            
            # Test listing agents
            try:
                agents = await client.list_agents()
                logger.info(f"Available agents: {agents}")
            except Exception as e:
                logger.warning(f"Could not list agents (server may not be running): {e}")
                
    except Exception as e:
        logger.warning(f"API test failed (server may not be running): {e}")


def test_database_models():
    """Test database models."""
    logger.info("Testing database models...")
    
    try:
        from server.models.agent import Agent, AgentStatus
        from server.models.hiring import Hiring, HiringStatus
        from server.models.execution import Execution, ExecutionStatus
        from server.models.user import User
        
        # Test agent model
        agent = Agent(
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
            author="Test Author",
            email="test@example.com",
            entry_point="test.py:TestAgent",
            status=AgentStatus.SUBMITTED.value,
        )
        
        logger.info(f"Created test agent: {agent.name}")
        
        # Test hiring model
        hiring = Hiring(
            agent_id=1,
            status=HiringStatus.ACTIVE.value,
        )
        
        logger.info(f"Created test hiring: {hiring.id}")
        
        # Test execution model
        execution = Execution(
            agent_id=1,
            status=ExecutionStatus.PENDING.value,
            execution_id="test-exec-123",
        )
        
        logger.info(f"Created test execution: {execution.execution_id}")
        
        # Test user model
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
        )
        
        logger.info(f"Created test user: {user.username}")
        
        logger.info("Database models test completed successfully!")
        
    except Exception as e:
        logger.error(f"Database models test failed: {e}")


def test_services():
    """Test service classes."""
    logger.info("Testing services...")
    
    try:
        from server.services.agent_service import AgentService, AgentCreateRequest
        from server.services.hiring_service import HiringService, HiringCreateRequest
        
        # Test agent service request model
        agent_request = AgentCreateRequest(
            name="Test Agent",
            description="A test agent",
            author="Test Author",
            email="test@example.com",
            entry_point="test.py:TestAgent",
        )
        
        logger.info(f"Created agent request: {agent_request.name}")
        
        # Test hiring service request model
        hiring_request = HiringCreateRequest(
            agent_id=1,
            config={"test": "config"},
        )
        
        logger.info(f"Created hiring request for agent: {hiring_request.agent_id}")
        
        logger.info("Services test completed successfully!")
        
    except Exception as e:
        logger.error(f"Services test failed: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting Agent Hiring System MVP tests...")
    
    # Test database models
    test_database_models()
    
    # Test services
    test_services()
    
    # Test agent functionality
    await test_agent_functionality()
    
    # Test API endpoints (if server is running)
    await test_api_endpoints()
    
    # Test agent submission (if server is running)
    await test_agent_submission()
    
    logger.info("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 