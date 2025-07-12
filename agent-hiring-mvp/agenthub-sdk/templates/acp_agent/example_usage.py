#!/usr/bin/env python3
"""
Example: How to customize the ACP Agent Template

This example shows how to extend the basic template to create
a specialized agent with custom functionality.
"""

import os 
from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel, VisitWebpageTool
import logging 
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server()

# Initialize the model (you can set OPENAI_API_KEY in .env file)
# model = LiteLLMModel(
#     model_id="openai/gpt-4",
#     max_tokens=2048
# )

@server.agent()
async def health_agent(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """This is a CodeAgent which supports the hospital to handle health based questions for patients."""
    
    try:
        # Get the input message
        prompt = input[0].parts[0].content
        
        # For now, provide a simple response without external tools
        if "rehabilitation" in prompt.lower() or "shoulder" in prompt.lower():
            response = "Yes, rehabilitation is typically recommended after shoulder reconstruction surgery. The rehabilitation process usually involves physical therapy to restore range of motion, strength, and function. Your surgeon and physical therapist will create a personalized rehabilitation plan based on your specific procedure and recovery needs."
        elif "hello" in prompt.lower() or "hi" in prompt.lower():
            response = "Hello! I'm your health assistant. I can help you with questions about medical procedures, rehabilitation, and general health information. How can I assist you today?"
        else:
            response = f"I understand you're asking about: '{prompt}'. As a health assistant, I can provide general information about medical procedures, rehabilitation, and health topics. For specific medical advice, please consult with your healthcare provider."
        
        yield Message(parts=[MessagePart(content=response)])
        
    except Exception as e:
        logger.error(f"Error in health_agent: {e}")
        yield Message(parts=[MessagePart(content="I apologize, but I encountered an error processing your request. Please try again.")])

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    
    logger.info(f"Starting ACP SDK server on {host}:{port}")
    server.run(host=host, port=port)