#!/usr/bin/env python3
"""
Script to demonstrate hiring an agent and executing a task without activation.

This script shows how to:
1. Create a user
2. Hire an agent directly (bypassing approval)
3. Execute a task immediately
4. Get the results

Usage:
    python scripts/hire_and_execute_direct.py
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
SERVER_URL = "http://localhost:8002"
API_BASE = f"{SERVER_URL}/api/v1"


def make_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Make an HTTP request to the API."""
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
            print(f"Status Code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return None


def create_user(username: str, email: str) -> Optional[Dict[str, Any]]:
    """Create a new user or get existing one."""
    print(f"Creating user: {username}")
    
    # First, try to get existing user
    existing_user = make_request("GET", f"/users/username/{username}")
    if existing_user:
        print(f"✅ User already exists: {existing_user['username']} (ID: {existing_user['id']})")
        return existing_user
    
    # Create new user if doesn't exist
    user_data = {
        "username": username,
        "email": email,
        "password": "testpassword123",
        "is_active": True,
        "preferences": {"theme": "dark"}
    }
    
    result = make_request("POST", "/users", user_data)
    if result:
        print(f"✅ User created: {result['username']} (ID: {result['id']})")
        return result
    else:
        print("❌ Failed to create user")
        return None


def get_available_agents() -> list:
    """Get list of available agents."""
    print("Fetching available agents...")
    
    result = make_request("GET", "/agents")
    if result:
        agents = result.get("agents", [])
        print(f"✅ Found {len(agents)} agents")
        return agents
    else:
        print("❌ Failed to fetch agents")
        return []


def hire_agent(agent_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Hire an agent directly."""
    print(f"Hiring agent {agent_id} for user {user_id}")
    
    hiring_data = {
        "agent_id": agent_id,
        "user_id": user_id,
        "requirements": {
            "task_type": "general",
            "priority": "high"
        },
        "budget": 100.0,
        "duration_hours": 24
    }
    
    result = make_request("POST", "/hiring", hiring_data)
    if result:
        print(f"✅ Agent hired successfully (Hiring ID: {result['id']})")
        return result
    else:
        print("❌ Failed to hire agent")
        return None


def execute_task(agent_id: int, hiring_id: int, user_id: int, task_input: str) -> Optional[Dict[str, Any]]:
    """Execute a task with the hired agent."""
    print(f"Executing task with agent {agent_id}")
    
    execution_data = {
        "agent_id": agent_id,
        "hiring_id": hiring_id,
        "user_id": user_id,
        "input_data": {
            "task": task_input,
            "parameters": {
                "timeout": 30,
                "max_iterations": 5
            }
        }
    }
    
    result = make_request("POST", "/execution", execution_data)
    if result:
        print(f"✅ Execution created (Execution ID: {result['execution_id']})")
        return result
    else:
        print("❌ Failed to create execution")
        return None


def run_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    """Run the execution and get results."""
    print(f"Running execution: {execution_id}")
    
    result = make_request("POST", f"/execution/{execution_id}/run")
    if result:
        print(f"✅ Execution completed")
        return result
    else:
        print("❌ Failed to run execution")
        return None


def get_execution_status(execution_id: str) -> Optional[Dict[str, Any]]:
    """Get execution status and details."""
    print(f"Checking execution status: {execution_id}")
    
    result = make_request("GET", f"/execution/{execution_id}")
    if result:
        print(f"✅ Execution status: {result['status']}")
        return result
    else:
        print("❌ Failed to get execution status")
        return None


def main():
    """Main workflow: Create user, hire agent, execute task."""
    print("🚀 Starting Hire and Execute Direct Workflow")
    print("=" * 50)
    
    # Step 1: Create a user
    user = create_user("testuser_direct", "testuser_direct@example.com")
    if not user:
        print("❌ Cannot continue without user")
        return
    
    user_id = user['id']
    
    # Step 2: Get available agents
    agents = get_available_agents()
    if not agents:
        print("❌ No agents available")
        return
    
    # Find and select the Calculator Agent
    calculator_agent = None
    for agent in agents:
        if agent['name'] == 'Calculator Agent':
            calculator_agent = agent
            break
    
    if not calculator_agent:
        print("❌ Calculator Agent not found, using first available agent")
        calculator_agent = agents[0]
    
    agent_id = calculator_agent['id']
    print(f"Selected agent: {calculator_agent['name']} (ID: {agent_id})")
    
    # Step 3: Hire the agent directly
    hiring = hire_agent(agent_id, user_id)
    if not hiring:
        print("❌ Cannot continue without hiring")
        return
    
    hiring_id = hiring['id']
    
    # Step 4: Execute a task
    task_input = "Calculate the sum of numbers from 1 to 100"
    execution = execute_task(agent_id, hiring_id, user_id, task_input)
    if not execution:
        print("❌ Cannot continue without execution")
        return
    
    execution_id = execution['execution_id']
    
    # Step 5: Run the execution
    print("\n🔄 Running execution...")
    result = run_execution(execution_id)
    
    if result:
        print("\n📊 Execution Results:")
        print("-" * 30)
        
        if result.get('status') == 'success':
            print(f"✅ Status: {result['status']}")
            print(f"⏱️  Execution Time: {result.get('execution_time', 'N/A')}ms")
            
            # Display output
            output = result.get('result', {})
            if 'output' in output:
                print(f"📝 Output: {output['output']}")
            else:
                print(f"📝 Full Result: {json.dumps(output, indent=2)}")
        else:
            print(f"❌ Status: {result.get('status', 'unknown')}")
            print(f"💥 Error: {result.get('error', 'Unknown error')}")
    
    # Step 6: Get final execution status
    print("\n📋 Final Execution Status:")
    print("-" * 30)
    final_status = get_execution_status(execution_id)
    if final_status:
        print(f"Status: {final_status['status']}")
        print(f"Created: {final_status['created_at']}")

        if final_status.get('output_data'):
            print(f"Output: {json.dumps(final_status['output_data'], indent=2)}")
        
        if final_status.get('error_message'):
            print(f"Error: {final_status['error_message']}")
    
    print("\n🎉 Workflow completed!")
    print("=" * 50)


if __name__ == "__main__":
    main() 