#!/usr/bin/env python3
"""
Example Usage for Resource Test Agent

This file demonstrates how to use the improved Resource Test Agent with all its
configurable parameters for CPU, memory, disk usage, duration, and success/failure control.
"""

import json
import time
from resource_test_agent import execute


def print_separator(title):
    """Print a formatted separator with title."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def run_example(description, input_data):
    """Run an example and display results."""
    print(f"\n--- {description} ---")
    print(f"Input: {json.dumps(input_data, indent=2)}")
    
    start_time = time.time()
    result = execute(input_data, {})
    execution_time = time.time() - start_time
    
    print(f"Execution time: {execution_time:.2f}s")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    return result


def main_examples():
    """Run all example scenarios."""
    print("Resource Test Agent - Example Usage")
    print("This demonstrates all configurable features of the agent.")
    
    # Example 1: Basic resource testing
    print_separator("Example 1: Basic Resource Testing")
    basic_input = {
        "task_type": "all",
        "cpu_percent": 50,
        "cpu_duration_seconds": 10,
        "memory_mb": 50,
        "memory_duration_seconds": 10,
        "disk_mb": 25,
        "disk_duration_seconds": 10
    }
    run_example("Basic resource testing with all resource types", basic_input)
    
    # Example 2: CPU-only high load testing
    print_separator("Example 2: CPU-Only High Load Testing")
    cpu_high_input = {
        "task_type": "cpu",
        "cpu_percent": 90,
        "cpu_duration_seconds": 15
    }
    run_example("CPU-only testing with 90% CPU usage for 15 seconds", cpu_high_input)
    
    # Example 3: Memory-only large allocation
    print_separator("Example 3: Memory-Only Large Allocation")
    memory_high_input = {
        "task_type": "memory",
        "memory_mb": 200,
        "memory_duration_seconds": 20
    }
    run_example("Memory-only testing with 200MB allocation for 20 seconds", memory_high_input)
    
    # Example 4: Disk-only heavy I/O
    print_separator("Example 4: Disk-Only Heavy I/O")
    disk_high_input = {
        "task_type": "disk",
        "disk_mb": 100,
        "disk_duration_seconds": 25
    }
    run_example("Disk-only testing with 100MB disk usage for 25 seconds", disk_high_input)
    
    # Example 5: Light load testing
    print_separator("Example 5: Light Load Testing")
    light_input = {
        "task_type": "all",
        "cpu_percent": 20,
        "cpu_duration_seconds": 8,
        "memory_mb": 25,
        "memory_duration_seconds": 8,
        "disk_mb": 10,
        "disk_duration_seconds": 8
    }
    run_example("Light load testing with minimal resource usage", light_input)
    
    # Example 6: Heavy load testing
    print_separator("Example 6: Heavy Load Testing")
    heavy_input = {
        "task_type": "all",
        "cpu_percent": 95,
        "cpu_duration_seconds": 20,
        "memory_mb": 500,
        "memory_duration_seconds": 20,
        "disk_mb": 250,
        "disk_duration_seconds": 20
    }
    run_example("Heavy load testing with maximum resource usage", heavy_input)
    
    # Example 7: Forced failure testing
    print_separator("Example 7: Forced Failure Testing")
    failure_input = {
        "task_type": "all",
        "should_succeed": False,
        "failure_probability": 1.0
    }
    run_example("Forced failure testing to test error handling", failure_input)
    
    # Example 8: Partial failure testing
    print_separator("Example 8: Partial Failure Testing")
    partial_failure_input = {
        "task_type": "all",
        "failure_probability": 0.5
    }
    run_example("Partial failure testing with 50% failure probability", partial_failure_input)
    
    # Example 9: Mixed resource testing with different durations
    print_separator("Example 9: Mixed Resource Testing with Different Durations")
    mixed_input = {
        "task_type": "all",
        "cpu_percent": 75,
        "cpu_duration_seconds": 30,
        "memory_mb": 150,
        "memory_duration_seconds": 45,
        "disk_mb": 75,
        "disk_duration_seconds": 60
    }
    run_example("Mixed resource testing with different durations for each resource type", mixed_input)
    
    # Example 10: Minimal resource testing
    print_separator("Example 10: Minimal Resource Testing")
    minimal_input = {
        "task_type": "all",
        "cpu_percent": 10,
        "cpu_duration_seconds": 5,
        "memory_mb": 10,
        "memory_duration_seconds": 5,
        "disk_mb": 5,
        "disk_duration_seconds": 5
    }
    run_example("Minimal resource testing for quick validation", minimal_input)
    
    print_separator("All Examples Completed")
    print("The Resource Test Agent has been demonstrated with various configurations.")
    print("You can now use these examples as templates for your own testing needs.")


def demonstrate_parameter_effects():
    """Demonstrate how different parameters affect resource usage."""
    print_separator("Parameter Effects Demonstration")
    
    print("\nCPU Percentage Effects:")
    print("- Lower percentages (10-30%): Light CPU load, good for baseline testing")
    print("- Medium percentages (40-70%): Moderate CPU load, realistic production scenarios")
    print("- High percentages (80-100%): Heavy CPU load, stress testing and limit validation")
    
    print("\nMemory Allocation Effects:")
    print("- Small allocations (10-100MB): Light memory pressure, good for basic testing")
    print("- Medium allocations (100-500MB): Moderate memory usage, typical container scenarios")
    print("- Large allocations (500MB-1GB+): Heavy memory pressure, stress testing")
    
    print("\nDisk Usage Effects:")
    print("- Small usage (5-50MB): Light disk I/O, basic I/O testing")
    print("- Medium usage (50-200MB): Moderate disk I/O, realistic file operations")
    print("- Large usage (200MB+): Heavy disk I/O, stress testing storage systems")
    
    print("\nDuration Effects:")
    print("- Short durations (5-15s): Quick tests, CI/CD pipelines, rapid validation")
    print("- Medium durations (15-60s): Standard testing, monitoring validation")
    print("- Long durations (1-60min): Stress testing, capacity planning, long-term monitoring")
    
    print("\nFailure Control:")
    print("- should_succeed: false: Guaranteed failure for error handling testing")
    print("- failure_probability: 0.0-1.0: Control failure rate for realistic testing scenarios")


if __name__ == "__main__":
    try:
        main_examples()
        demonstrate_parameter_effects()
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        print("Make sure the resource_test_agent.py file is in the same directory.")
