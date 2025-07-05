#!/usr/bin/env python3
"""
Simple Echo Agent
This agent simply echoes back the input message with some processing.
"""

def main():
    """Main agent function."""
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

if __name__ == "__main__":
    main() 