#!/usr/bin/env python3
"""
Test script for the BeeAI Hiring System API
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_list_agents():
    """Test listing all agents"""
    print("🤖 Testing List Agents...")
    response = requests.get(f"{BASE_URL}/api/v1/hiring/agents")
    print(f"Status: {response.status_code}")
    agents = response.json()["agents"]
    print(f"Found {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent['name']} (${agent['hourly_rate']}/hr, Rating: {agent['rating']})")
    print()

def test_get_agent():
    """Test getting a specific agent"""
    print("🔍 Testing Get Agent...")
    response = requests.get(f"{BASE_URL}/api/v1/hiring/agents/agent-1")
    print(f"Status: {response.status_code}")
    agent = response.json()["agent"]
    print(f"Agent: {agent['name']}")
    print(f"Skills: {', '.join(agent['skills'])}")
    print(f"Description: {agent['description']}")
    print()

def test_create_task():
    """Test creating a new task"""
    print("📝 Testing Create Task...")
    task_data = {
        "title": "Data Analysis Project",
        "description": "Analyze customer data and create visualizations",
        "agent_id": "agent-1",
        "budget": 500.0
    }
    response = requests.post(f"{BASE_URL}/api/v1/hiring/tasks", json=task_data)
    print(f"Status: {response.status_code}")
    task = response.json()["task"]
    print(f"Created task: {task['title']} (ID: {task['id']})")
    print(f"Budget: ${task['budget']}, Status: {task['status']}")
    print()
    return task["id"]

def test_list_tasks():
    """Test listing all tasks"""
    print("📋 Testing List Tasks...")
    response = requests.get(f"{BASE_URL}/api/v1/hiring/tasks")
    print(f"Status: {response.status_code}")
    tasks = response.json()["tasks"]
    print(f"Found {len(tasks)} tasks:")
    for task in tasks:
        print(f"  - {task['title']} (Status: {task['status']}, Budget: ${task['budget']})")
    print()

def test_update_task_status(task_id):
    """Test updating task status"""
    print("🔄 Testing Update Task Status...")
    status_data = {"status": "in_progress"}
    response = requests.put(f"{BASE_URL}/api/v1/hiring/tasks/{task_id}/status", json=status_data)
    print(f"Status: {response.status_code}")
    task = response.json()["task"]
    print(f"Updated task {task['id']} status to: {task['status']}")
    print()

def test_credits():
    """Test credits functionality"""
    print("💰 Testing Credits...")
    
    # Get current credits
    response = requests.get(f"{BASE_URL}/api/v1/hiring/credits")
    print(f"Current credits: ${response.json()['credits']['user_credits']}")
    
    # Add credits
    add_data = {"amount": 250.0}
    response = requests.post(f"{BASE_URL}/api/v1/hiring/credits/add", json=add_data)
    print(f"Added ${add_data['amount']} credits")
    
    # Get updated credits
    response = requests.get(f"{BASE_URL}/api/v1/hiring/credits")
    print(f"Updated credits: ${response.json()['credits']['user_credits']}")
    print()

def main():
    """Run all tests"""
    print("🚀 Testing BeeAI Hiring System API")
    print("=" * 50)
    
    try:
        test_health_check()
        test_list_agents()
        test_get_agent()
        task_id = test_create_task()
        test_list_tasks()
        test_update_task_status(task_id)
        test_credits()
        
        print("✅ All tests completed successfully!")
        print("\n🌐 You can also visit:")
        print(f"   - API Documentation: {BASE_URL}/docs")
        print(f"   - Health Check: {BASE_URL}/health")
        print(f"   - Hiring API: {BASE_URL}/api/v1/hiring")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the server.")
        print("Make sure the development server is running on port 8001")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 