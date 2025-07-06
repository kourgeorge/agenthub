#!/usr/bin/env python3
"""
Complete Agent Creation and Publishing Workflow

This example demonstrates the complete process of:
1. Creating an agent with proper structure
2. Writing agent code
3. Publishing to the platform
4. Testing the published agent

This example works without the SDK and shows the manual process.
"""

import os
import sys
import json
import tempfile
import zipfile
import requests
from pathlib import Path
from typing import Dict, Any


def create_agent_structure(base_dir: str) -> str:
    """Create a complete agent directory structure."""
    agent_dir = Path(base_dir) / "calculator_agent"
    agent_dir.mkdir(exist_ok=True)
    
    # Create the main agent file
    agent_code = '''#!/usr/bin/env python3
"""
Calculator Agent - Performs mathematical calculations.
"""

import json
from typing import Dict, Any


def calculate(operation: str, a: float, b: float) -> float:
    """Perform basic mathematical operations."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
        "power": lambda x, y: x ** y,
        "modulo": lambda x, y: x % y if y != 0 else None
    }
    
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    
    return operations[operation](a, b)


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main agent function.
    
    Args:
        input_data: User input containing operation and numbers
        config: Agent configuration (precision, rounding, etc.)
    
    Returns:
        Calculation result
    """
    try:
        # Get configuration
        precision = config.get("precision", 2)
        rounding = config.get("rounding", True)
        
        # Get input data
        operation = input_data.get("operation", "add")
        a = float(input_data.get("a", 0))
        b = float(input_data.get("b", 0))
        
        # Validate operation
        valid_operations = ["add", "subtract", "multiply", "divide", "power", "modulo"]
        if operation not in valid_operations:
            return {
                "error": f"Invalid operation. Supported operations: {valid_operations}",
                "status": "error"
            }
        
        # Perform calculation
        result = calculate(operation, a, b)
        
        if result is None:
            return {
                "error": "Division by zero or invalid operation",
                "status": "error"
            }
        
        # Apply rounding if configured
        if rounding:
            result = round(result, precision)
        
        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
            "precision": precision,
            "status": "success"
        }
        
    except ValueError as e:
        return {
            "error": f"Invalid input: {str(e)}",
            "status": "error"
        }
    except Exception as e:
        return {
            "error": f"Calculation failed: {str(e)}",
            "status": "error"
        }


# For testing
if __name__ == "__main__":
    # Test the agent
    test_input = {
        "operation": "add",
        "a": 5,
        "b": 3
    }
    
    test_config = {
        "precision": 2,
        "rounding": True
    }
    
    result = main(test_input, test_config)
    print(json.dumps(result, indent=2))
'''
    
    # Write the agent code
    with open(agent_dir / "calculator_agent.py", "w") as f:
        f.write(agent_code)
    
    # Create requirements.txt
    requirements = '''# No external dependencies required for basic calculations
# Add any additional dependencies here if needed
'''
    
    with open(agent_dir / "requirements.txt", "w") as f:
        f.write(requirements)
    
    # Create README.md
    readme = '''# Calculator Agent

A simple mathematical calculator agent that performs basic operations.

## Features

- Basic arithmetic operations (add, subtract, multiply, divide)
- Power and modulo operations
- Configurable precision and rounding
- Input validation and error handling

## Supported Operations

- `add`: Addition (a + b)
- `subtract`: Subtraction (a - b)
- `multiply`: Multiplication (a * b)
- `divide`: Division (a / b)
- `power`: Exponentiation (a ^ b)
- `modulo`: Modulo (a % b)

## Usage

The agent accepts the following input format:

```json
{
    "operation": "add",
    "a": 5,
    "b": 3
}
```

## Configuration

- `precision` (optional): Number of decimal places (default: 2)
- `rounding` (optional): Whether to round results (default: true)

## Example Response

```json
{
    "operation": "add",
    "a": 5,
    "b": 3,
    "result": 8,
    "precision": 2,
    "status": "success"
}
```

## Error Handling

The agent returns error messages for:
- Invalid operations
- Division by zero
- Invalid input types
- Calculation errors
'''
    
    with open(agent_dir / "README.md", "w") as f:
        f.write(readme)
    
    return str(agent_dir)


def create_agent_zip(agent_dir: str) -> str:
    """Create a ZIP file from the agent directory."""
    agent_path = Path(agent_dir)
    zip_path = agent_path.parent / "calculator_agent.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in agent_path.rglob('*'):
            if file_path.is_file():
                # Get relative path for ZIP
                relative_path = file_path.relative_to(agent_path)
                zip_file.write(file_path, relative_path)
    
    return str(zip_path)


def submit_agent_to_platform(agent_zip_path: str, base_url: str = "http://localhost:8002") -> Dict[str, Any]:
    """Submit the agent to the platform."""
    
    # Agent configuration
    agent_config = {
        "name": "calculator-agent",
        "description": "A mathematical calculator agent that performs basic arithmetic operations",
        "version": "1.0.0",
        "author": "AgentHub Demo",
        "email": "demo@agenthub.com",
        "entry_point": "calculator_agent.py",
        "requirements": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "precision": {
                    "type": "integer",
                    "default": 2,
                    "description": "Number of decimal places for results"
                },
                "rounding": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to round results"
                }
            }
        },
        "tags": ["calculator", "math", "arithmetic"],
        "category": "utilities",
        "pricing_model": "per_use",
        "price_per_use": 0.001,
        "monthly_price": None
    }
    
    # Prepare form data
    with open(agent_zip_path, 'rb') as f:
        files = {
            'code_file': ('calculator_agent.zip', f, 'application/zip')
        }
        
        data = {
            'name': agent_config['name'],
            'description': agent_config['description'],
            'version': agent_config['version'],
            'author': agent_config['author'],
            'email': agent_config['email'],
            'entry_point': agent_config['entry_point'],
            'requirements': json.dumps(agent_config['requirements']),
            'config_schema': json.dumps(agent_config['config_schema']),
            'tags': json.dumps(agent_config['tags']),
            'category': agent_config['category'],
            'pricing_model': agent_config['pricing_model'],
            'price_per_use': str(agent_config['price_per_use']),
            'monthly_price': str(agent_config['monthly_price']) if agent_config['monthly_price'] else ''
        }
        
        # Submit to platform
        response = requests.post(
            f"{base_url}/api/v1/agents/submit",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Submission failed: {response.status_code} - {response.text}")


def test_agent_execution(agent_id: int, base_url: str = "http://localhost:8002") -> Dict[str, Any]:
    """Test the agent execution."""
    
    # First, hire the agent
    hire_data = {
        "agent_id": agent_id,
        "config": {"precision": 2, "rounding": True},
        "billing_cycle": "per_use"
    }
    
    hire_response = requests.post(
        f"{base_url}/api/v1/hiring/hire/{agent_id}",
        json=hire_data,
        timeout=30
    )
    
    if hire_response.status_code != 200:
        raise Exception(f"Hiring failed: {hire_response.status_code} - {hire_response.text}")
    
    hire_result = hire_response.json()
    hiring_id = hire_result.get("hiring_id")
    
    print(f"✅ Agent hired successfully! Hiring ID: {hiring_id}")
    
    # Test different calculations
    test_cases = [
        {"operation": "add", "a": 5, "b": 3},
        {"operation": "multiply", "a": 4, "b": 7},
        {"operation": "divide", "a": 15, "b": 3},
        {"operation": "power", "a": 2, "b": 8}
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧮 Testing calculation {i}: {test_case['operation']}({test_case['a']}, {test_case['b']})")
        
        # Execute the agent
        execution_data = {
            "agent_id": agent_id,
            "input_data": test_case,
            "hiring_id": hiring_id
        }
        
        exec_response = requests.post(
            f"{base_url}/api/v1/execution",
            json=execution_data,
            timeout=30
        )
        
        if exec_response.status_code != 200:
            print(f"❌ Execution failed: {exec_response.text}")
            continue
        
        execution_result = exec_response.json()
        execution_id = execution_result.get("execution_id")
        
        # Wait for completion
        print(f"⏳ Waiting for execution {execution_id} to complete...")
        
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = requests.get(
                f"{base_url}/api/v1/execution/{execution_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_result = status_response.json()
                execution = status_result.get("execution", {})
                status = execution.get("status")
                
                if status == "completed":
                    result = execution.get("result", {})
                    print(f"✅ Result: {result.get('result', 'No result')}")
                    results.append(result)
                    break
                elif status == "failed":
                    error = execution.get("error", "Unknown error")
                    print(f"❌ Execution failed: {error}")
                    break
                elif attempt == max_attempts - 1:
                    print("⏰ Execution timeout")
                    break
            else:
                print(f"❌ Status check failed: {status_response.text}")
                break
            
            import time
            time.sleep(1)
    
    return results


def main():
    """Main workflow function."""
    print("🧮 Calculator Agent Creation and Publishing Workflow")
    print("=" * 60)
    
    base_url = "http://localhost:8002"
    
    try:
        # Step 1: Create agent structure
        print("📁 Step 1: Creating agent structure...")
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_dir = create_agent_structure(temp_dir)
            print(f"✅ Agent structure created in: {agent_dir}")
            
            # Step 2: Create ZIP file
            print("\n📦 Step 2: Creating agent ZIP file...")
            zip_path = create_agent_zip(agent_dir)
            print(f"✅ Agent ZIP created: {zip_path}")
            
            # Step 3: Submit to platform
            print("\n📤 Step 3: Submitting agent to platform...")
            result = submit_agent_to_platform(zip_path, base_url)
            agent_id = result.get("agent_id")
            print(f"✅ Agent submitted successfully!")
            print(f"   Agent ID: {agent_id}")
            print(f"   Status: {result.get('status')}")
            
            # Step 4: Test agent execution
            print("\n🚀 Step 4: Testing agent execution...")
            test_results = test_agent_execution(agent_id, base_url)
            
            print(f"\n📊 Test Results Summary:")
            print(f"   Total tests: {len(test_results)}")
            print(f"   Successful: {len([r for r in test_results if r.get('status') == 'success'])}")
            
            # Step 5: List available agents
            print("\n📋 Step 5: Listing available agents...")
            agents_response = requests.get(f"{base_url}/api/v1/agents", timeout=10)
            
            if agents_response.status_code == 200:
                agents_data = agents_response.json()
                agents = agents_data.get("agents", [])
                print(f"✅ Found {len(agents)} agents:")
                for agent in agents:
                    print(f"   - {agent['name']} (ID: {agent['id']}) - {agent['status']}")
            else:
                print(f"❌ Failed to list agents: {agents_response.text}")
        
        print("\n🎉 Workflow completed successfully!")
        print("\nNext steps:")
        print("1. The calculator agent is now available on the platform")
        print("2. Users can hire and execute the agent")
        print("3. You can view the agent in the web interface")
        print("4. The agent will need approval before being publicly available")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the server is running on port 8002")
        print("2. Check that all dependencies are installed")
        print("3. Verify the server is accessible")
        print("4. Check server logs for detailed error messages")


if __name__ == "__main__":
    main() 