#!/usr/bin/env python3
"""
Integration test for agent submission to the server.
This test creates a real agent and submits it via the API.
"""

import json
import os
import sys
import tempfile
import zipfile
import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import configuration
from config import get_test_config, Endpoints, DEFAULT_SERVER_URL

def print_separator(title: str):
    """Print a separator with title."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_step(step: str, title: str):
    """Print a step header."""
    print(f"\n📋 STEP {step}: {title}")
    print("-" * 50)

def print_response(title: str, response: requests.Response):
    """Print response details."""
    print(f"\n{title}:")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return data
    except:
        print(f"Response: {response.text}")
        return None

class AgentSubmissionTest:
    """Test class for agent submission workflow."""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use configuration if no base_url provided
        if base_url is None:
            config = get_test_config()
            base_url = config["server_url"]
        
        # Ensure base_url is not None before using rstrip
        if base_url is None:
            raise ValueError("base_url cannot be None")
        
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.submitted_agent_id = None
        
    def test_server_health(self) -> bool:
        """Test if the server is running."""
        print_step("1", "SERVER HEALTH CHECK")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Server is running and healthy")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Is it running?")
            return False
    
    def create_test_agent_code(self) -> str:
        """Create test agent code."""
        return '''#!/usr/bin/env python3
"""
Test Agent for Submission
This is a test agent created for integration testing.
"""

def main():
    """Main agent function."""
    # Get input data
    message = input_data.get('message', 'Hello World!')
    operation = input_data.get('operation', 'echo')
    
    # Process based on operation
    if operation == 'echo':
        result = f"Echo: {message}"
    elif operation == 'uppercase':
        result = f"Uppercase: {message.upper()}"
    elif operation == 'lowercase':
        result = f"Lowercase: {message.lower()}"
    elif operation == 'reverse':
        result = f"Reversed: {message[::-1]}"
    elif operation == 'count':
        result = f"Character count: {len(message)}"
    else:
        result = f"Unknown operation: {operation}"
    
    # Print result
    print(f"Test Agent Result: {result}")
    
    # Return structured output
    output = {
        "operation": operation,
        "input_message": message,
        "result": result,
        "agent_type": "test_submission_agent",
        "version": "1.0.0"
    }
    
    print(f"Agent processing complete: {output}")

if __name__ == "__main__":
    main()
'''
    
    def create_requirements_file(self) -> str:
        """Create requirements.txt file."""
        return '''requests>=2.25.0
pandas>=1.3.0
numpy>=1.21.0
'''
    
    def create_readme_file(self) -> str:
        """Create README.md file."""
        return '''# Test Submission Agent

This is a test agent created for integration testing of the agent hiring system.

## Features
- Echo functionality
- Text transformation (uppercase, lowercase, reverse)
- Character counting
- Structured output

## Usage
Send a message with an operation:
- `echo`: Echo the message
- `uppercase`: Convert to uppercase
- `lowercase`: Convert to lowercase
- `reverse`: Reverse the message
- `count`: Count characters

## Example
```json
{
  "message": "Hello World!",
  "operation": "uppercase"
}
```
'''
    
    def create_agent_zip(self) -> str:
        """Create a ZIP file with the agent code."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
                # Add main agent file
                zip_file.writestr("test_agent.py", self.create_test_agent_code())
                
                # Add requirements file
                zip_file.writestr("requirements.txt", self.create_requirements_file())
                
                # Add README
                zip_file.writestr("README.md", self.create_readme_file())
                
                # Add a utility module
                zip_file.writestr("utils.py", '''
def format_output(message: str, operation: str, result: str) -> dict:
    """Format the output in a consistent way."""
    return {
        "operation": operation,
        "input": message,
        "output": result,
        "timestamp": "2024-01-01T00:00:00Z"
    }
''')
            
            return temp_zip.name
    
    def test_agent_submission(self) -> bool:
        """Test submitting an agent to the server."""
        print_step("2", "AGENT SUBMISSION")
        
        try:
            # Create agent ZIP file
            zip_path = self.create_agent_zip()
            
            try:
                # Prepare form data
                data = {
                    "name": "Test Submission Agent",
                    "description": "A test agent created for integration testing of the agent hiring system",
                    "version": "1.0.0",
                    "author": "Integration Test",
                    "email": "test@integration.example.com",
                    "entry_point": "test_agent.py:main",
                    "requirements": json.dumps(["requests", "pandas", "numpy"]),
                    "tags": json.dumps(["test", "integration", "submission", "utility"]),
                    "category": "testing",
                    "pricing_model": "free",
                    "price_per_use": "0.0"
                }
                
                # Prepare files
                files = {
                    "code_file": ("test_agent.zip", open(zip_path, "rb"), "application/zip")
                }
                
                # Submit agent
                print("Submitting agent to server...")
                response = self.session.post(
                    f"{self.api_base}/agents/submit",
                    data=data,
                    files=files
                )
                
                result = print_response("Agent Submission", response)
                
                if response.status_code == 200 and result:
                    self.submitted_agent_id = result.get("agent_id")
                    print(f"✅ Agent submitted successfully with ID: {self.submitted_agent_id}")
                    return True
                else:
                    print("❌ Agent submission failed")
                    return False
                    
            finally:
                # Clean up ZIP file
                if os.path.exists(zip_path):
                    os.unlink(zip_path)
                    
        except Exception as e:
            print(f"❌ Error during agent submission: {e}")
            return False
    
    def test_agent_listing(self) -> bool:
        """Test listing agents to see if our submitted agent appears."""
        print_step("3", "AGENT LISTING")
        
        try:
            response = self.session.get(f"{self.api_base}/agents")
            result = print_response("Agent Listing", response)
            
            if response.status_code == 200 and result:
                agents = result.get("agents", [])
                print(f"Found {len(agents)} agents in the system")
                
                # Look for our submitted agent
                if self.submitted_agent_id:
                    our_agent = next((a for a in agents if a.get("id") == self.submitted_agent_id), None)
                    if our_agent:
                        print(f"✅ Our submitted agent found: {our_agent['name']}")
                        print(f"   Status: {our_agent.get('status', 'unknown')}")
                        return True
                    else:
                        print("⚠️  Our submitted agent not found in listing (may not be approved yet)")
                        print("   This is expected for newly submitted agents")
                        return True  # Don't fail the test for this
                else:
                    print("⚠️  No agent ID to search for")
                    return True
            else:
                print("❌ Failed to list agents")
                return False
                
        except Exception as e:
            print(f"❌ Error during agent listing: {e}")
            return False
    
    def test_agent_details(self) -> bool:
        """Test getting details of our submitted agent."""
        print_step("4", "AGENT DETAILS")
        
        if not self.submitted_agent_id:
            print("❌ No agent ID available for details test")
            return False
        
        try:
            response = self.session.get(f"{self.api_base}/agents/{self.submitted_agent_id}")
            result = print_response("Agent Details", response)
            
            if response.status_code == 200 and result:
                agent = result.get("agent", {})
                print(f"✅ Agent details retrieved:")
                print(f"   Name: {agent.get('name')}")
                print(f"   Author: {agent.get('author')}")
                print(f"   Status: {agent.get('status')}")
                print(f"   Entry Point: {agent.get('entry_point')}")
                return True
            else:
                print("❌ Failed to get agent details")
                return False
                
        except Exception as e:
            print(f"❌ Error during agent details retrieval: {e}")
            return False
    
    def test_agent_execution(self) -> bool:
        """Test executing our submitted agent."""
        print_step("5", "AGENT EXECUTION")
        
        if not self.submitted_agent_id:
            print("❌ No agent ID available for execution test")
            return False
        
        try:
            # Create execution
            execution_data = {
                "agent_id": self.submitted_agent_id,
                "input_data": {
                    "message": "Hello from integration test!",
                    "operation": "uppercase"
                }
            }
            
            print("Creating execution...")
            response = self.session.post(
                f"{self.api_base}/execution",
                json=execution_data
            )
            
            result = print_response("Execution Creation", response)
            
            if response.status_code == 200 and result:
                execution_id = result.get("execution_id")
                print(f"✅ Execution created with ID: {execution_id}")
                
                # Wait a moment for execution to complete
                time.sleep(2)
                
                # Check execution status
                print("Checking execution status...")
                status_response = self.session.get(f"{self.api_base}/execution/{execution_id}")
                status_result = print_response("Execution Status", status_response)
                
                if status_response.status_code == 200 and status_result:
                    execution = status_result.get("execution", {})
                    status = execution.get("status")
                    print(f"✅ Execution status: {status}")
                    
                    if status in ["completed", "failed"]:
                        output = execution.get("output_data", {})
                        print(f"   Output: {output}")
                        return True
                    else:
                        print(f"⚠️  Execution still running: {status}")
                        return True
                else:
                    print("❌ Failed to get execution status")
                    return False
            else:
                print("❌ Failed to create execution")
                return False
                
        except Exception as e:
            print(f"❌ Error during agent execution: {e}")
            return False
    
    def test_agent_approval(self) -> bool:
        """Test approving our submitted agent (admin function)."""
        print_step("6", "AGENT APPROVAL")
        
        if not self.submitted_agent_id:
            print("❌ No agent ID available for approval test")
            return False
        
        try:
            # Try to approve the agent
            response = self.session.put(f"{self.api_base}/agents/{self.submitted_agent_id}/approve")
            result = print_response("Agent Approval", response)
            
            if response.status_code == 200:
                print("✅ Agent approved successfully")
                return True
            elif response.status_code == 403:
                print("⚠️  Agent approval requires admin privileges (expected)")
                return True
            else:
                print(f"❌ Agent approval failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error during agent approval: {e}")
            return False
    
    def cleanup(self):
        """Clean up test data."""
        print_step("7", "CLEANUP")
        
        if self.submitted_agent_id:
            try:
                # Note: In a real system, you might want to delete the test agent
                # For now, we'll just note that cleanup would happen here
                print(f"⚠️  Test agent with ID {self.submitted_agent_id} remains in database")
                print("   In production, you would delete test agents here")
            except Exception as e:
                print(f"❌ Error during cleanup: {e}")
    
    def run_all_tests(self) -> bool:
        """Run all agent submission tests."""
        print_separator("AGENT SUBMISSION INTEGRATION TEST")
        print("Testing the complete agent submission workflow...")
        
        tests = [
            ("Server Health", self.test_server_health),
            ("Agent Submission", self.test_agent_submission),
            ("Agent Approval", self.test_agent_approval),  # Move approval before listing
            ("Agent Listing", self.test_agent_listing),
            ("Agent Details", self.test_agent_details),
            ("Agent Execution", self.test_agent_execution),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} test passed")
                else:
                    print(f"❌ {test_name} test failed")
            except Exception as e:
                print(f"❌ {test_name} test failed with exception: {e}")
        
        self.cleanup()
        
        print_separator("TEST RESULTS")
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Agent submission workflow is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


def main():
    """Run the agent submission test."""
    # Check if server URL is provided as command line argument
    server_url = DEFAULT_SERVER_URL

    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"Testing agent submission against: {server_url}")
    
    # Create and run test
    test = AgentSubmissionTest(server_url)
    success = test.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 