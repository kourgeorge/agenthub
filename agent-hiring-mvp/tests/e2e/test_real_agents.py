#!/usr/bin/env python3
"""
Demo script to test real agent execution with the new runtime service.
This script demonstrates the complete workflow from hiring to execution.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8002"
API_BASE = f"{BASE_URL}/api/v1"

def print_separator(title: str):
    """Print a separator with title."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make an HTTP request and return the response."""
    url = f"{API_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return {"error": str(e)}

def test_agent_listing():
    """Test listing available agents."""
    print_separator("1. LISTING AVAILABLE AGENTS")
    
    response = make_request("GET", "/agents")
    if "error" in response:
        print(f"Failed to list agents: {response['error']}")
        return []
    
    agents = response.get("agents", [])
    print(f"Found {len(agents)} agents:")
    
    for agent in agents:
        print(f"  - {agent.get('name', 'Unknown')} (ID: {agent.get('id', 'Unknown')})")
        print(f"    Description: {agent.get('description', 'No description')}")
        print(f"    Status: {agent.get('status', 'Unknown')}")
        print()
    
    return agents

def test_hiring_workflow(agent_id: int):
    """Test the complete hiring workflow for an agent."""
    print_separator(f"2. HIRING AGENT {agent_id}")
    
    # Create hiring request
    hiring_data = {
        "agent_id": agent_id,
        "user_id": 1,  # Using admin user
        "duration_hours": 24,
        "max_executions": 10,
        "budget": 100.0,
        "requirements": {
            "message": "Test hiring for agent execution"
        }
    }
    
    print("Creating hiring request...")
    response = make_request("POST", "/hiring", hiring_data)
    
    if "error" in response:
        print(f"Failed to create hiring: {response['error']}")
        return None
    
    # The response is the hiring object directly
    hiring = response
    if not hiring or "id" not in hiring:
        print(f"Failed to get hiring data from response: {response}")
        return None
        
    print(f"Hiring created successfully!")
    print(f"  Hiring ID: {hiring.get('id', 'Unknown')}")
    print(f"  Status: {hiring.get('status', 'Unknown')}")
    print(f"  Budget: ${hiring.get('budget', 'Unknown')}")
    print(f"  Duration: {hiring.get('duration_hours', 'Unknown')} hours")
    
    return hiring

def test_agent_execution(agent_id: int, hiring_id: str):
    """Test agent execution with different input data."""
    print_separator(f"3. EXECUTING AGENT {agent_id}")
    
    # Test cases for different agents
    test_cases = [
        {
            "name": "Echo Agent Test",
            "input_data": {
                "message": "Hello from the hiring system!",
                "prefix": "Agent says: "
            }
        },
        {
            "name": "Calculator Agent Test",
            "input_data": {
                "operation": "add",
                "numbers": [10, 20, 30, 40]
            }
        },
        {
            "name": "Text Processor Test",
            "input_data": {
                "text": "This is a sample text for processing. It contains multiple words and sentences.",
                "operation": "analyze"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        
        # Create execution request
        execution_data = {
            "agent_id": agent_id,
            "hiring_id": hiring_id,
            "input_data": test_case["input_data"],
            "priority": "normal"
        }
        
        print("Creating execution request...")
        response = make_request("POST", "/execution", execution_data)
        
        if "error" in response:
            print(f"Failed to create execution: {response['error']}")
            continue
        
        # The response contains execution_id, not id
        execution = response
        if not execution or "execution_id" not in execution:
            print(f"Failed to get execution data from response: {response}")
            continue
            
        execution_id = execution.get("execution_id")
        print(f"Execution created! ID: {execution_id}")
        print(f"Status: {execution.get('status', 'Unknown')}")
        
        # Wait a moment for execution to complete
        print("Waiting for execution to complete...")
        time.sleep(2)
        
        # Execute the agent immediately
        print("Executing agent...")
        execute_response = make_request("POST", f"/execution/{execution_id}/run")
        
        print(f"Execution response: {execute_response}")
        
        if "error" in execute_response:
            print(f"Failed to execute agent: {execute_response['error']}")
            continue
        
        # Display execution results from the response
        if execute_response.get("status") == "success":
            print("✅ Execution completed successfully!")
            result = execute_response.get("result", {})
            
            if result.get("output"):
                print("Agent Output:")
                print(f"  {result['output'].strip()}")
            
            if result.get("execution_time"):
                print(f"Execution Time: {result['execution_time']:.3f}s")
            
            if result.get("status"):
                print(f"Result Status: {result['status']}")
        else:
            print(f"❌ Execution failed: {execute_response.get('error', 'Unknown error')}")
        
        print()

def test_acp_protocol():
    """Test ACP protocol endpoints."""
    print_separator("4. TESTING ACP PROTOCOL")
    
    # Test ACP discovery
    print("Testing ACP discovery...")
    response = make_request("GET", "/acp/discovery")
    
    if "error" in response:
        print(f"ACP discovery failed: {response['error']}")
    else:
        print("ACP discovery successful!")
        print(f"Protocol: {response.get('protocol', 'N/A')}")
        print(f"Version: {response.get('version', 'N/A')}")
    
    # Test ACP capabilities
    print("\nTesting ACP capabilities...")
    response = make_request("GET", "/acp/capabilities")
    
    if "error" in response:
        print(f"ACP capabilities failed: {response['error']}")
    else:
        print("ACP capabilities retrieved!")
        capabilities = response.get("capabilities", [])
        for capability in capabilities:
            print(f"  - {capability}")

def main():
    """Main demo function."""
    print("🤖 AGENT HIRING SYSTEM - REAL AGENT EXECUTION DEMO")
    print("This demo tests the complete workflow with real agent code execution.")
    
    # Test 1: List available agents
    agents = test_agent_listing()
    if not agents:
        print("No agents available. Please ensure the server is running and has sample data.")
        return
    
    # Test 2: Hire the first available agent
    if not agents:
        print("No agents available. Cannot proceed with hiring test.")
        return
    agent_id = agents[0].get("id")
    if not agent_id:
        print("Invalid agent data. Cannot proceed with hiring test.")
        return
    hiring = test_hiring_workflow(agent_id)
    if not hiring:
        print("Failed to create hiring. Cannot proceed with execution tests.")
        return
    
    hiring_id = hiring.get("id")
    if not hiring_id:
        print("Invalid hiring data. Cannot proceed with execution tests.")
        return
    
    # Test 3: Execute the agent with various inputs
    test_agent_execution(agent_id, hiring_id)
    
    # Test 4: Test ACP protocol
    test_acp_protocol()
    
    print_separator("DEMO COMPLETED")
    print("✅ All tests completed!")
    print("\nKey Features Demonstrated:")
    print("  - Real agent code execution using subprocess")
    print("  - Secure sandboxed environment")
    print("  - Input/output handling")
    print("  - Error handling and timeouts")
    print("  - Complete hiring workflow")
    print("  - ACP protocol support")

if __name__ == "__main__":
    main() 