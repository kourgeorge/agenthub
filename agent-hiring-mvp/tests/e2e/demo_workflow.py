#!/usr/bin/env python3
"""
Demo script showing how to hire an agent and run requests against it.
This demonstrates the complete workflow of the AI Agent Hiring System.
"""
import os
import sys

import requests
import json
import time

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from typing import Dict, Any
from config import DEFAULT_SERVER_URL

# Configuration
BASE_URL = DEFAULT_SERVER_URL
API_BASE = f"{BASE_URL}/api/v1"

def print_step(step: str, description: str):
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {description}")
    print(f"{'='*60}")

def print_response(title: str, response: requests.Response):
    """Print a formatted API response."""
    print(f"\n{title}:")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def demo_agent_hiring_workflow():
    """Demonstrate the complete agent hiring and execution workflow."""
    
    print("🚀 AI AGENT HIRING SYSTEM - COMPLETE WORKFLOW DEMO")
    print("=" * 60)
    
    # Step 1: List available agents
    print_step("1", "BROWSE AVAILABLE AGENTS")
    print("Let's see what agents are available for hiring...")
    
    response = requests.get(f"{API_BASE}/agents/")
    print_response("Available Agents", response)
    
    if response.status_code != 200:
        print("❌ Failed to get agents. Make sure the server is running!")
        return
    
    agents_data = response.json()
    agents = agents_data.get("agents", [])
    if not agents:
        print("❌ No agents available. Please check the database.")
        return
    
    # Select the first available agent
    agent = agents[0]
    agent_id = agent["id"]
    agent_name = agent["name"]
    
    print(f"\n✅ Selected agent: {agent_name} (ID: {agent_id})")
    
    # Step 2: Create a hiring request
    print_step("2", "HIRE THE AGENT")
    print(f"Creating a hiring request for {agent_name}...")
    
    hiring_data = {
        "agent_id": agent_id,
        "user_id": 1,  # Using sample user
        "requirements": {
            "task_type": "data_analysis",
            "priority": "high",
            "expected_duration": "2 hours"
        },
        "budget": 50.0,
        "duration_hours": 2
    }
    
    response = requests.post(f"{API_BASE}/hiring/", json=hiring_data)
    print_response("Hiring Request Created", response)
    
    if response.status_code != 200:
        print("❌ Failed to create hiring request!")
        return
    
    hiring = response.json()
    hiring_id = hiring["id"]
    
    print(f"✅ Hiring request created with ID: {hiring_id}")
    
    # Step 3: Activate the hiring (approve it)
    print_step("3", "ACTIVATE THE HIRING")
    print("Approving the hiring request...")
    
    response = requests.put(f"{API_BASE}/hiring/{hiring_id}/activate")
    print_response("Hiring Activated", response)
    
    if response.status_code != 200:
        print("❌ Failed to activate hiring!")
        return
    
    print("✅ Hiring is now active!")
    
    # Step 4: Create an execution
    print_step("4", "CREATE AN EXECUTION")
    print("Creating an execution to run the agent...")
    
    execution_data = {
        "agent_id": agent_id,
        "hiring_id": hiring_id,
        "user_id": 1,
        "input_data": {
            "message": "Hello! I need help analyzing some data.",
            "data": "Sample dataset for analysis",
            "requirements": "Please provide insights and recommendations"
        }
    }
    
    response = requests.post(f"{API_BASE}/execution/", json=execution_data)
    print_response("Execution Created", response)
    
    if response.status_code != 200:
        print("❌ Failed to create execution!")
        return
    
    execution = response.json()
    execution_id = execution["execution_id"]
    
    print(f"✅ Execution created with ID: {execution_id}")
    
    # Step 5: Run the execution
    print_step("5", "RUN THE AGENT")
    print("Executing the agent...")
    
    response = requests.post(f"{API_BASE}/execution/{execution_id}/run")
    print_response("Agent Execution Result", response)
    
    if response.status_code != 200:
        print("❌ Failed to run execution!")
        return
    
    result = response.json()
    print("✅ Agent execution completed successfully!")
    
    # Step 6: Check execution status
    print_step("6", "CHECK EXECUTION STATUS")
    print("Getting detailed execution information...")
    
    response = requests.get(f"{API_BASE}/execution/{execution_id}")
    print_response("Execution Details", response)
    
    # Step 7: Demonstrate ACP Protocol Information
    print_step("7", "ACP (AGENT COMMUNICATION PROTOCOL) INFO")
    print("Getting ACP protocol information...")
    
    # Get ACP discovery info
    response = requests.get(f"{API_BASE}/acp/discovery")
    print_response("ACP Discovery", response)
    
    # Get ACP capabilities
    response = requests.get(f"{API_BASE}/acp/capabilities")
    print_response("ACP Capabilities", response)
    
    print("Note: For actual agent communication, use the deployment + agent-proxy workflow:")
    print("  1. Create deployment: POST /deployment/create/{hiring_id}")
    print("  2. Chat with agent: POST /agent-proxy/chat/{hiring_id}")
    print("  3. Get agent info: GET /agent-proxy/info/{hiring_id}")
    
    # Step 8: View hiring statistics
    print_step("8", "VIEW STATISTICS")
    print("Getting hiring and execution statistics...")
    
    # Hiring stats
    response = requests.get(f"{API_BASE}/hiring/stats/user/1")
    print_response("User Hiring Statistics", response)
    
    # Execution stats
    response = requests.get(f"{API_BASE}/execution/stats/agent/{agent_id}")
    print_response("Agent Execution Statistics", response)
    
    # Step 9: List user's hirings
    print_step("9", "VIEW USER HIRINGS")
    print("Listing all hirings for the user...")
    
    response = requests.get(f"{API_BASE}/hiring/user/1")
    print_response("User Hirings", response)
    
    # Step 10: List agent executions
    print_step("10", "VIEW AGENT EXECUTIONS")
    print("Listing all executions for the agent...")
    
    response = requests.get(f"{API_BASE}/execution/agent/{agent_id}")
    print_response("Agent Executions", response)
    
    print("\n" + "="*60)
    print("🎉 DEMO COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nThis demo showed the complete workflow:")
    print("1. ✅ Browse available agents")
    print("2. ✅ Hire an agent")
    print("3. ✅ Activate the hiring")
    print("4. ✅ Create an execution")
    print("5. ✅ Run the agent")
    print("6. ✅ Check execution status")
    print("7. ✅ ACP protocol information")
    print("8. ✅ View statistics")
    print("9. ✅ List user hirings")
    print("10. ✅ List agent executions")
    
    print(f"\n🌐 API Documentation: {BASE_URL}/docs")
    print(f"📊 ReDoc Documentation: {BASE_URL}/redoc")
    print(f"🔗 Base API URL: {API_BASE}")

def demo_simple_agent_execution():
    """Demonstrate a simple agent execution without hiring."""
    
    print("\n" + "="*60)
    print("🔧 SIMPLE AGENT EXECUTION DEMO (No Hiring Required)")
    print("="*60)
    
    # Get available agents
    response = requests.get(f"{API_BASE}/agents/")
    if response.status_code != 200:
        print("❌ Failed to get agents!")
        return
    
    agents_data = response.json()
    agents = agents_data.get("agents", [])
    if not agents:
        print("❌ No agents available!")
        return
    
    agent = agents[0]
    agent_id = agent["id"]
    
    print(f"Using agent: {agent['name']} (ID: {agent_id})")
    
    # Create direct execution
    execution_data = {
        "agent_id": agent_id,
        "input_data": {
            "message": "Hello from direct execution!",
            "task": "simple_echo"
        }
    }
    
    response = requests.post(f"{API_BASE}/execution/", json=execution_data)
    print_response("Direct Execution Created", response)
    
    if response.status_code == 200:
        execution = response.json()
        execution_id = execution["execution_id"]
        
        # Run the execution
        response = requests.post(f"{API_BASE}/execution/{execution_id}/run")
        print_response("Direct Execution Result", response)
    
    print("✅ Simple execution demo completed!")

if __name__ == "__main__":
    try:
        # Test server connection
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not responding. Make sure it's running on port 8002!")
            print("Start the server with: python -m server.main --dev --port 8002")
            exit(1)
        
        print("✅ Server is running and responding!")
        
        # Run the main demo
        demo_agent_hiring_workflow()
        
        # Run the simple demo
        demo_simple_agent_execution()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on port 8002!")
        print("Start the server with: python -m server.main --dev --port 8002")
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        print("Make sure the server is running and accessible.") 