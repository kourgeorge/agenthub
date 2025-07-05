#!/usr/bin/env python3
"""
Calculator Agent
This agent performs mathematical operations on input data.
"""

def main():
    """Main agent function."""
    # Get input data
    operation = input_data.get('operation', 'add')
    numbers = input_data.get('numbers', [1, 2])
    
    # Validate input
    if not isinstance(numbers, list) or len(numbers) < 2:
        print("Error: At least 2 numbers required")
        return
    
    # Perform calculation
    result = None
    if operation == 'add':
        result = sum(numbers)
    elif operation == 'multiply':
        result = 1
        for num in numbers:
            result *= num
    elif operation == 'subtract':
        result = numbers[0] - sum(numbers[1:])
    elif operation == 'divide':
        if 0 in numbers[1:]:
            print("Error: Division by zero")
            return
        result = numbers[0]
        for num in numbers[1:]:
            result /= num
    else:
        print(f"Error: Unknown operation '{operation}'")
        return
    
    # Format output
    print(f"Operation: {operation}")
    print(f"Numbers: {numbers}")
    print(f"Result: {result}")
    
    # Return structured result
    output = {
        "operation": operation,
        "numbers": numbers,
        "result": result,
        "agent_type": "calculator"
    }
    
    print(f"Calculation complete: {output}")

if __name__ == "__main__":
    main() 