#!/usr/bin/env python3
"""
Example usage of the Resource Test Agent
This file demonstrates how to use the agent with various configurations.
Note: This agent uses only Python standard library modules for maximum compatibility.
"""
from resource_test_agent import main


def example_light_test():
    """Example of a light resource test."""
    print("=== Light Resource Test Example ===")
    
    input_data = {
        "task_type": "both",
        "intensity": 2
    }
    
    print(f"Input: {input_data}")
    result = main(input_data, {})
    
    print(f"Result: {result}")
    return result


def example_cpu_only_test():
    """Example of a CPU-only test."""
    print("\n=== CPU-Only Test Example ===")
    
    input_data = {
        "task_type": "cpu",
        "intensity": 4
    }
    
    print(f"Input: {input_data}")
    result = main(input_data, {})
    
    print(f"Result: {result}")
    return result


def example_memory_only_test():
    """Example of a memory-only test."""
    print("\n=== Memory-Only Test Example ===")
    
    input_data = {
        "task_type": "memory",
        "intensity": 3
    }
    
    print(f"Input: {input_data}")
    result = main(input_data, {})
    
    print(f"Result: {result}")
    return result


def example_heavy_test():
    """Example of a heavy resource test (use with caution)."""
    print("\n=== Heavy Resource Test Example ===")
    
    input_data = {
        "task_type": "both",
        "intensity": 7
    }
    
    print(f"Input: {input_data}")
    print("Warning: This is a heavy test that may take several minutes!")
    
    result = main(input_data, {})
    
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    print("Resource Test Agent - Example Usage")
    print("Note: Uses Python standard library only for maximum compatibility")
    print("=" * 60)
    
    # Run light test
    example_light_test()
    
    # Run CPU-only test
    example_cpu_only_test()
    
    # Run memory-only test
    example_memory_only_test()
    
    # Uncomment the line below to run a heavy test (use with caution)
    # example_heavy_test()
    
    print("\nAll examples completed!")
