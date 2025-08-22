#!/usr/bin/env python3
"""
Enhanced Echo Agent

This agent echoes back input messages with enhanced processing capabilities:
- Message transformation (uppercase, repetition)
- Comprehensive metadata tracking
- Input validation
- Error handling
- Proper schema compliance
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize input data according to the inputSchema.
    
    Args:
        input_data: Raw input data from the user
        
    Returns:
        Validated and sanitized input data
        
    Raises:
        ValueError: If input validation fails
    """
    if not isinstance(input_data, dict):
        raise ValueError("Input data must be a dictionary")
    
    # Extract and validate message (required)
    message = input_data.get('message')
    if not message or not isinstance(message, str):
        raise ValueError("'message' is required and must be a non-empty string")
    
    if len(message) > 1000:
        raise ValueError("Message length must not exceed 1000 characters")
    
    # Extract and validate prefix (optional)
    prefix = input_data.get('prefix', 'Echo: ')
    if not isinstance(prefix, str):
        raise ValueError("'prefix' must be a string")
    
    if len(prefix) > 100:
        raise ValueError("Prefix length must not exceed 100 characters")
    
    # Extract and validate uppercase flag (optional)
    uppercase = input_data.get('uppercase', False)
    if not isinstance(uppercase, bool):
        raise ValueError("'uppercase' must be a boolean")
    
    # Extract and validate repeat count (optional)
    repeat_count = input_data.get('repeat_count', 1)
    if not isinstance(repeat_count, int):
        raise ValueError("'repeat_count' must be an integer")
    
    if repeat_count < 1 or repeat_count > 10:
        raise ValueError("'repeat_count' must be between 1 and 10")
    
    return {
        'message': message,
        'prefix': prefix,
        'uppercase': uppercase,
        'repeat_count': repeat_count
    }


def process_message(message: str, prefix: str, uppercase: bool, repeat_count: int) -> str:
    """
    Process the message according to the specified parameters.
    
    Args:
        message: The original message to process
        prefix: Prefix to add before the message
        uppercase: Whether to convert to uppercase
        repeat_count: Number of times to repeat the message
        
    Returns:
        Processed message string
    """
    # Apply transformations
    processed_message = message
    
    if uppercase:
        processed_message = processed_message.upper()
    
    # Apply prefix and repetition
    result = prefix + processed_message
    
    if repeat_count > 1:
        result = (result + '\n') * (repeat_count - 1) + result
    
    return result


def generate_metadata(
    original_message: str, 
    final_response: str, 
    prefix: str, 
    uppercase: bool, 
    repeat_count: int
) -> Dict[str, Any]:
    """
    Generate comprehensive metadata about the processing.
    
    Args:
        original_message: The original input message
        final_response: The final processed response
        prefix: The prefix that was applied
        uppercase: Whether uppercase was applied
        repeat_count: The number of repetitions
        
    Returns:
        Metadata dictionary
    """
    return {
        "prefix_used": prefix,
        "uppercase_applied": uppercase,
        "repeat_count": repeat_count,
        "message_length": len(original_message),
        "response_length": len(final_response)
    }


def execute(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main execution function for the Echo Agent.
    
    This function implements the execute function defined in the config_schema.
    It processes input messages according to the specified parameters and returns
    output that strictly conforms to the outputSchema.
    
    Args:
        input_data: Input data containing message and optional parameters
        config: Optional configuration (not used in this simple agent)
        
    Returns:
        Dictionary conforming to the outputSchema
    """
    try:
        logger.info("Starting Echo Agent execution")
        
        # Validate input data
        validated_input = validate_input(input_data)
        message = validated_input['message']
        prefix = validated_input['prefix']
        uppercase = validated_input['uppercase']
        repeat_count = validated_input['repeat_count']
        
        logger.info(f"Processing message: '{message}' with prefix: '{prefix}', uppercase: {uppercase}, repeat: {repeat_count}")
        
        # Process the message
        response = process_message(message, prefix, uppercase, repeat_count)
        
        # Generate metadata
        processing_metadata = generate_metadata(message, response, prefix, uppercase, repeat_count)
        
        # Generate current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Construct result according to outputSchema
        result = {
            "response": response,
            "original_message": message,
            "timestamp": timestamp,
            "agent_type": "echo"
        }
        
        logger.info(f"Echo Agent execution completed successfully. Response length: {len(response)}")
        
        # Print result for debugging (captured by runtime)
        print(f"Agent Response: {response}")
        print(f"Processing complete for message: {message}")
        
        return result
        
    except ValueError as e:
        # Input validation error
        logger.error(f"Input validation error: {e}")
        error_result = {
            "response": f"Error: {str(e)}",
            "original_message": input_data.get('message', 'Invalid input'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": "echo"
        }
        
        print(f"Agent Error: {str(e)}")
        return error_result
        
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in Echo Agent: {e}")
        error_result = {
            "response": f"Unexpected error: {str(e)}",
            "original_message": input_data.get('message', 'Unknown'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": "echo"
        }
        
        print(f"Agent Error: {str(e)}")
        return error_result


def main(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for the agent.
    
    This function is called by the AgentHub runtime and delegates to execute().
    It maintains backward compatibility with the old function signature.
    
    Args:
        input_data: Input data from the user
        config: Optional configuration
        
    Returns:
        Execution result
    """
    return execute(input_data, config)


if __name__ == "__main__":
    # Test the agent locally
    test_input = {
        "message": "Hello, World!",
        "prefix": "Echo: ",
        "uppercase": False,
        "repeat_count": 2
    }
    
    print("🧪 Testing Echo Agent Locally")
    print("=" * 40)
    print(f"Input: {json.dumps(test_input, indent=2)}")
    print()
    
    result = execute(test_input)
    
    print("Result:")
    print(json.dumps(result, indent=2))
    
    # Test error case
    print("\n" + "=" * 40)
    print("Testing error case (empty message):")
    
    error_input = {"message": ""}
    error_result = execute(error_input)
    
    print("Error Result:")
    print(json.dumps(error_result, indent=2)) 