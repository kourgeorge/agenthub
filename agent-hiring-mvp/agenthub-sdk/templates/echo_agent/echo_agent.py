#!/usr/bin/env python3
"""
Simple Echo Agent
This agent simply echoes back the input message with some processing.
"""

def main(input_data=None, config=None):
    """Main agent function."""
    # Use provided input_data or load from file as fallback
    if input_data is None:
        try:
            import json
            with open('input.json', 'r') as f:
                input_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            input_data = {}
    
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
    
    # Return the result (this is what the runtime expects)
    return result

if __name__ == "__main__":
    main() 