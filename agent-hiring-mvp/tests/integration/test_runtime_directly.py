#!/usr/bin/env python3
"""
Direct test of the agent runtime service.
This script tests the runtime without going through the full server.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from server.services.agent_runtime import AgentRuntimeService, RuntimeStatus

def test_echo_agent():
    """Test the echo agent."""
    print("🧪 Testing Echo Agent...")
    
    runtime = AgentRuntimeService()
    
    # Test case 1: Basic echo
    result = runtime.execute_agent(
        agent_id=1,
        input_data={"message": "Hello World!", "prefix": "Echo: "},
        agent_code='''
def main():
    message = input_data.get('message', 'Hello World!')
    prefix = input_data.get('prefix', 'Echo: ')
    response = f"{prefix}{message}"
    print(f"Agent Response: {response}")
    print(f"Processing complete for message: {message}")

if __name__ == "__main__":
    main()
'''
    )
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print()

def test_calculator_agent():
    """Test the calculator agent."""
    print("🧮 Testing Calculator Agent...")
    
    runtime = AgentRuntimeService()
    
    # Test case 1: Addition
    result = runtime.execute_agent(
        agent_id=2,
        input_data={"operation": "add", "numbers": [10, 20, 30]},
        agent_code='''
def main():
    operation = input_data.get('operation', 'add')
    numbers = input_data.get('numbers', [1, 2])
    
    if not isinstance(numbers, list) or len(numbers) < 2:
        print("Error: At least 2 numbers required")
        return
    
    result = None
    if operation == 'add':
        result = sum(numbers)
    elif operation == 'multiply':
        result = 1
        for num in numbers:
            result *= num
    else:
        print(f"Error: Unknown operation '{operation}'")
        return
    
    print(f"Operation: {operation}")
    print(f"Numbers: {numbers}")
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
'''
    )
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print()

def test_text_processor_agent():
    """Test the text processor agent."""
    print("📝 Testing Text Processor Agent...")
    
    runtime = AgentRuntimeService()
    
    # Test case 1: Text analysis
    result = runtime.execute_agent(
        agent_id=3,
        input_data={
            "text": "This is a sample text for processing.",
            "operation": "analyze"
        },
        agent_code='''
def main():
    text = input_data.get('text', 'Hello World!')
    operation = input_data.get('operation', 'analyze')
    
    if operation == 'analyze':
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.splitlines())
        
        print(f"Text Analysis Results:")
        print(f"Word count: {word_count}")
        print(f"Character count: {char_count}")
        print(f"Line count: {line_count}")
        print(f"Average word length: {char_count / word_count if word_count > 0 else 0:.2f}")
    else:
        print(f"Error: Unknown operation '{operation}'")

if __name__ == "__main__":
    main()
'''
    )
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print()

def test_security_violations():
    """Test security violation detection."""
    print("🛡️ Testing Security Violations...")
    
    runtime = AgentRuntimeService()
    
    # Test case 1: Forbidden command
    result = runtime.execute_agent(
        agent_id=4,
        input_data={"message": "test"},
        agent_code='''
def main():
    print("This is a test")
    print("rm -rf /")  # This should trigger security violation
    print("sudo shutdown")  # This should also trigger

if __name__ == "__main__":
    main()
'''
    )
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Security Violations: {result.security_violations}")
    print()

def test_timeout():
    """Test timeout handling."""
    print("⏰ Testing Timeout...")
    
    runtime = AgentRuntimeService()
    
    # Test case 1: Infinite loop (should timeout)
    result = runtime.execute_agent(
        agent_id=5,
        input_data={"message": "test"},
        agent_code='''
def main():
    print("Starting infinite loop...")
    while True:
        pass  # This should timeout

if __name__ == "__main__":
    main()
'''
    )
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print()

def main():
    """Run all tests."""
    print("🚀 AGENT RUNTIME DIRECT TEST")
    print("Testing the agent runtime service directly...")
    print()
    
    try:
        test_echo_agent()
        test_calculator_agent()
        test_text_processor_agent()
        test_security_violations()
        test_timeout()
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 