#!/usr/bin/env python3
"""
Resource Test Agent
This agent performs CPU and memory intensive tasks to test Docker monitoring systems.
Uses only Python standard library modules for maximum compatibility.
"""
import time
import math
import random
import array
import gc
from typing import Dict, Any


def cpu_intensive_task(intensity: int) -> Dict[str, Any]:
    """Perform CPU intensive calculations based on intensity level."""
    start_time = time.time()
    
    # Scale the workload based on intensity (1-10)
    iterations = intensity * 100000
    matrix_size = intensity * 50
    
    print(f"Starting CPU intensive task with {iterations:,} iterations and {matrix_size}x{matrix_size} matrices...")
    
    # Matrix operations (CPU intensive) using standard library
    matrices = []
    for i in range(intensity * 2):
        # Create random matrices using standard library
        matrix = []
        for row in range(matrix_size):
            matrix_row = []
            for col in range(matrix_size):
                matrix_row.append(random.random())
            matrix.append(matrix_row)
        matrices.append(matrix)
    
    # Perform matrix operations
    result_matrix = [[1.0 if i == j else 0.0 for j in range(matrix_size)] for i in range(matrix_size)]
    
    for matrix in matrices:
        # Simple matrix multiplication
        temp_matrix = [[0.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
        for i in range(matrix_size):
            for j in range(matrix_size):
                for k in range(matrix_size):
                    temp_matrix[i][j] += result_matrix[i][k] * matrix[k][j]
        result_matrix = temp_matrix
    
    # Additional CPU work
    for i in range(iterations):
        if i % 10000 == 0:
            # Progress indicator
            progress = (i / iterations) * 100
            print(f"CPU progress: {progress:.1f}%")
        
        # Perform mathematical operations
        result = math.sqrt(i + 1) * math.sin(i) * math.cos(i)
        result = math.exp(result / 1000) if result != 0 else 1
    
    cpu_time = time.time() - start_time
    print(f"CPU intensive task completed in {cpu_time:.2f} seconds")
    
    return {
        "task_type": "cpu",
        "iterations": iterations,
        "matrix_size": matrix_size,
        "execution_time": cpu_time,
        "result_summary": f"Processed {len(matrices)} matrices of size {matrix_size}x{matrix_size}"
    }


def memory_intensive_task(intensity: int) -> Dict[str, Any]:
    """Perform memory intensive operations based on intensity level."""
    start_time = time.time()
    
    # Scale memory usage based on intensity (1-10)
    # Each intensity level adds ~50MB of memory usage
    memory_mb = intensity * 50
    memory_bytes = memory_mb * 1024 * 1024
    
    print(f"Starting memory intensive task using ~{memory_mb}MB of memory...")
    
    # Create large data structures using standard library
    large_arrays = []
    total_allocated = 0
    
    # Allocate memory in chunks
    chunk_size = 1024 * 1024  # 1MB chunks
    num_chunks = memory_bytes // chunk_size
    
    for i in range(num_chunks):
        # Create arrays of different types to stress memory
        if i % 3 == 0:
            # Float arrays
            array_data = array.array('d', [random.random() for _ in range(chunk_size // 8)])
        elif i % 3 == 1:
            # Integer arrays
            array_data = array.array('l', [random.randint(0, 1000000) for _ in range(chunk_size // 8)])
        else:
            # String arrays
            array_data = [f"string_{j}" for j in range(chunk_size // 100)]
        
        large_arrays.append(array_data)
        total_allocated += len(str(array_data)) * 8  # Rough estimate
        
        if i % 10 == 0:
            progress = (i / num_chunks) * 100
            print(f"Memory allocation progress: {progress:.1f}% ({total_allocated / (1024*1024):.1f}MB)")
    
    # Perform operations on the data
    print("Performing operations on allocated memory...")
    results = []
    for i, array_data in enumerate(large_arrays):
        if hasattr(array_data, 'typecode') and array_data.typecode in 'dl':
            # Numeric arrays
            result = sum(array_data) + (sum(array_data) / len(array_data)) if array_data else 0
        else:
            # String arrays
            result = len(array_data)
        results.append(result)
    
    # Clean up some memory
    del large_arrays[:len(large_arrays)//2]
    gc.collect()  # Force garbage collection
    
    memory_time = time.time() - start_time
    
    # Estimate memory usage (rough calculation)
    estimated_memory = len(large_arrays) * chunk_size / (1024 * 1024)
    
    print(f"Memory intensive task completed in {memory_time:.2f} seconds")
    print(f"Estimated memory usage: {estimated_memory:.1f}MB")
    
    return {
        "task_type": "memory",
        "allocated_memory_mb": memory_mb,
        "estimated_memory_mb": estimated_memory,
        "execution_time": memory_time,
        "num_arrays_created": len(large_arrays),
        "result_summary": f"Allocated and processed ~{memory_mb}MB of data"
    }


def main(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Main agent function."""
    # Get input parameters
    task_type = input_data.get('task_type', 'both')
    intensity = input_data.get('intensity', 5)
    
    # Validate intensity
    intensity = max(1, min(10, intensity))
    
    print(f"Resource Test Agent starting...")
    print(f"Task type: {task_type}")
    print(f"Intensity level: {intensity}")
    print(f"Using Python standard library only")
    
    start_time = time.time()
    results = {}
    
    try:
        if task_type in ['cpu', 'both']:
            print("\n=== Starting CPU Intensive Task ===")
            results['cpu_task'] = cpu_intensive_task(intensity)
        
        if task_type in ['memory', 'both']:
            print("\n=== Starting Memory Intensive Task ===")
            results['memory_task'] = memory_intensive_task(intensity)
        
        total_time = time.time() - start_time
        
        print(f"\n=== Resource Test Complete ===")
        print(f"Total execution time: {total_time:.2f} seconds")
        
        result = {
            "status": "success",
            "task_type": task_type,
            "intensity_level": intensity,
            "total_execution_time": total_time,
            "task_results": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_type": "resource_test",
            "note": "Uses Python standard library only for maximum compatibility"
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e),
            "task_type": task_type,
            "intensity_level": intensity,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_type": "resource_test"
        }
        print(f"Error occurred: {e}")
        return error_result


if __name__ == "__main__":
    # Test with default parameters
    test_input = {
        "task_type": "both",
        "intensity": 3
    }
    result = main(test_input, {})
    print(f"\nTest result: {result}")
