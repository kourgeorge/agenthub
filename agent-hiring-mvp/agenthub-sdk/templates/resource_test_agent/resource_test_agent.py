#!/usr/bin/env python3
"""
Resource Test Agent
This agent performs configurable CPU, memory, and disk intensive tasks to test Docker monitoring systems.
Uses only Python standard library modules for maximum compatibility.
"""
import time
import math
import random
import array
import gc
import os
import tempfile
import shutil
from typing import Dict, Any, Optional


def cpu_intensive_task(cpu_percent: int, duration_seconds: int) -> Dict[str, Any]:
    """Perform CPU intensive calculations with configurable CPU usage and duration."""
    start_time = time.time()
    target_end_time = start_time + duration_seconds
    
    # Calculate work intervals to achieve target CPU percentage
    # Higher CPU percent means more work per time unit
    work_multiplier = cpu_percent / 100.0
    
    print(f"Starting CPU intensive task targeting {cpu_percent}% CPU usage for {duration_seconds} seconds...")
    
    # Matrix operations (CPU intensive) using standard library
    matrix_size = int(50 * work_multiplier)
    matrices = []
    
    # Create initial matrices (ensure at least 1 matrix)
    num_matrices = max(1, int(5 * work_multiplier))
    for i in range(num_matrices):
        matrix = []
        for row in range(matrix_size):
            matrix_row = []
            for col in range(matrix_size):
                matrix_row.append(random.random())
            matrix.append(matrix_row)
        matrices.append(matrix)
    
    # Perform matrix operations until target duration is reached
    result_matrix = [[1.0 if i == j else 0.0 for j in range(matrix_size)] for i in range(matrix_size)]
    iterations = 0
    
    while time.time() < target_end_time:
        # Create new matrices periodically to maintain memory pressure
        if iterations % 100 == 0 and len(matrices) < 20 and iterations > 0:
            new_matrix = []
            for row in range(matrix_size):
                matrix_row = []
                for col in range(matrix_size):
                    matrix_row.append(random.random())
                new_matrix.append(matrix_row)
            matrices.append(new_matrix)
        
        # Perform matrix multiplication
        temp_matrix = [[0.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
        matrix_index = iterations % len(matrices)
        for i in range(matrix_size):
            for j in range(matrix_size):
                for k in range(matrix_size):
                    temp_matrix[i][j] += result_matrix[i][k] * matrices[matrix_index][k][j]
        result_matrix = temp_matrix
        
        # Additional CPU work based on target percentage
        for i in range(int(1000 * work_multiplier)):
            result = math.sqrt(i + 1) * math.sin(i) * math.cos(i)
            result = math.exp(result / 1000) if result != 0 else 1
        
        iterations += 1
        
        # Progress indicator
        if iterations % 100 == 0:
            elapsed = time.time() - start_time
            progress = (elapsed / duration_seconds) * 100
            print(f"CPU progress: {progress:.1f}% ({elapsed:.1f}s/{duration_seconds}s)")
    
    cpu_time = time.time() - start_time
    print(f"CPU intensive task completed in {cpu_time:.2f} seconds")
    
    return {
        "task_type": "cpu",
        "target_cpu_percent": cpu_percent,
        "target_duration_seconds": duration_seconds,
        "actual_duration_seconds": cpu_time,
        "iterations_completed": iterations,
        "matrix_size": matrix_size,
        "execution_time": cpu_time,
        "result_summary": f"Processed {iterations} iterations with {len(matrices)} matrices of size {matrix_size}x{matrix_size}"
    }


def memory_intensive_task(memory_mb: int, duration_seconds: int) -> Dict[str, Any]:
    """Perform memory intensive operations with configurable memory usage and duration."""
    start_time = time.time()
    target_end_time = start_time + duration_seconds
    
    print(f"Starting memory intensive task using ~{memory_mb}MB of memory for {duration_seconds} seconds...")
    
    # Create large data structures using standard library
    large_arrays = []
    total_allocated = 0
    
    # Allocate memory in chunks
    chunk_size = 1024 * 1024  # 1MB chunks
    num_chunks = memory_mb
    
    # Allocate initial memory
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
    
    # Perform operations on the data until target duration is reached
    operations = 0
    while time.time() < target_end_time:
        # Perform operations on the data
        for i, array_data in enumerate(large_arrays):
            if hasattr(array_data, 'typecode') and array_data.typecode in 'dl':
                # Numeric arrays
                result = sum(array_data) + (sum(array_data) / len(array_data)) if array_data else 0
            else:
                # String arrays
                result = len(array_data)
            
            # Add some CPU work to maintain memory pressure
            if operations % 1000 == 0:
                # Create temporary arrays to stress memory management
                temp_array = array.array('d', [random.random() for _ in range(1000)])
                del temp_array
        
        operations += 1
        
        # Progress indicator
        if operations % 1000 == 0:
            elapsed = time.time() - start_time
            progress = (elapsed / duration_seconds) * 100
            print(f"Memory operations progress: {progress:.1f}% ({elapsed:.1f}s/{duration_seconds}s)")
    
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
        "target_memory_mb": memory_mb,
        "target_duration_seconds": duration_seconds,
        "actual_duration_seconds": memory_time,
        "allocated_memory_mb": memory_mb,
        "estimated_memory_mb": estimated_memory,
        "execution_time": memory_time,
        "num_arrays_created": len(large_arrays),
        "operations_completed": operations,
        "result_summary": f"Allocated and processed ~{memory_mb}MB of data for {memory_time:.1f} seconds"
    }


def disk_intensive_task(disk_mb: int, duration_seconds: int) -> Dict[str, Any]:
    """Perform disk intensive operations with configurable disk usage and duration."""
    start_time = time.time()
    target_end_time = start_time + duration_seconds
    
    print(f"Starting disk intensive task using ~{disk_mb}MB of disk space for {duration_seconds} seconds...")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="resource_test_")
    files_created = []
    total_disk_used = 0
    
    try:
        # Create files until target disk usage is reached
        file_counter = 0
        while total_disk_used < disk_mb and time.time() < target_end_time:
            # Create file with random data
            filename = os.path.join(temp_dir, f"test_file_{file_counter}.dat")
            
            # Each file is 1MB
            file_size_mb = 1
            file_size_bytes = file_size_mb * 1024 * 1024
            
            with open(filename, 'wb') as f:
                # Write random data in chunks
                chunk_size = 1024 * 1024  # 1MB chunks
                for i in range(file_size_mb):
                    chunk_data = os.urandom(chunk_size)
                    f.write(chunk_data)
            
            files_created.append(filename)
            total_disk_used += file_size_mb
            file_counter += 1
            
            # Progress indicator
            if file_counter % 10 == 0:
                elapsed = time.time() - start_time
                progress = (elapsed / duration_seconds) * 100
                print(f"Disk write progress: {progress:.1f}% ({elapsed:.1f}s/{duration_seconds}s) - {total_disk_used}MB written")
        
        # Perform read operations until target duration is reached
        read_operations = 0
        while time.time() < target_end_time:
            # Read from random files
            for filename in files_created:
                if time.time() >= target_end_time:
                    break
                
                try:
                    with open(filename, 'rb') as f:
                        # Read file in chunks
                        chunk_size = 1024 * 1024  # 1MB chunks
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            # Process chunk (simple hash-like operation)
                            chunk_sum = sum(chunk)
                
                except Exception as e:
                    print(f"Warning: Error reading file {filename}: {e}")
                
                read_operations += 1
                
                # Progress indicator
                if read_operations % 100 == 0:
                    elapsed = time.time() - start_time
                    progress = (elapsed / duration_seconds) * 100
                    print(f"Disk read progress: {progress:.1f}% ({elapsed:.1f}s/{duration_seconds}s) - {read_operations} read operations")
        
        disk_time = time.time() - start_time
        
        print(f"Disk intensive task completed in {disk_time:.2f} seconds")
        print(f"Total disk usage: {total_disk_used}MB")
        
        return {
            "task_type": "disk",
            "target_disk_mb": disk_mb,
            "target_duration_seconds": duration_seconds,
            "actual_duration_seconds": disk_time,
            "actual_disk_mb": total_disk_used,
            "files_created": len(files_created),
            "read_operations": read_operations,
            "execution_time": disk_time,
            "result_summary": f"Created {len(files_created)} files using {total_disk_used}MB of disk space for {disk_time:.1f} seconds"
        }
    
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary directory {temp_dir}: {e}")


def health_check() -> Dict[str, Any]:
    """Simple health check function to verify agent is working."""
    return {
        "status": "healthy",
        "agent_type": "resource_test",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "message": "Resource Test Agent is ready"
    }


def execute(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main agent function."""
    try:
        # Ensure config is a dictionary
        if config is None:
            config = {}
        
        # Get input parameters with defaults
        task_type = input_data.get('task_type', 'all')
        cpu_percent = input_data.get('cpu_percent', 50)
        cpu_duration = input_data.get('cpu_duration_seconds', 30)
        memory_mb = input_data.get('memory_mb', 100)
        memory_duration = input_data.get('memory_duration_seconds', 30)
        disk_mb = input_data.get('disk_mb', 50)
        disk_duration = input_data.get('disk_duration_seconds', 30)
        should_succeed = input_data.get('should_succeed', True)
        failure_probability = input_data.get('failure_probability', 0.0)
        
        # Validate parameters with more conservative limits
        cpu_percent = max(1, min(90, cpu_percent))  # Cap at 90% to prevent system overload
        cpu_duration = max(1, min(300, cpu_duration))  # Max 5 minutes to prevent timeouts
        memory_mb = max(1, min(1000, memory_mb))  # Max 1GB to prevent memory issues
        memory_duration = max(1, min(300, memory_duration))  # Max 5 minutes
        disk_mb = max(1, min(500, disk_mb))  # Max 500MB to prevent disk space issues
        disk_duration = max(1, min(300, disk_duration))  # Max 5 minutes
        failure_probability = max(0.0, min(1.0, failure_probability))
        
        print(f"Resource Test Agent starting...")
        print(f"Task type: {task_type}")
        print(f"CPU: {cpu_percent}% for {cpu_duration}s")
        print(f"Memory: {memory_mb}MB for {memory_duration}s")
        print(f"Disk: {disk_mb}MB for {disk_duration}s")
        print(f"Should succeed: {should_succeed}")
        print(f"Failure probability: {failure_probability:.1%}")
        print(f"Using Python standard library only")
        
        start_time = time.time()
        results = {}
        
        # Check if we should fail based on probability
        if not should_succeed or random.random() < failure_probability:
            # Simulate a failure
            failure_type = random.choice(['cpu_error', 'memory_error', 'disk_error', 'timeout_error'])
            
            if failure_type == 'cpu_error':
                raise RuntimeError("Simulated CPU task failure")
            elif failure_type == 'memory_error':
                raise MemoryError("Simulated memory allocation failure")
            elif failure_type == 'disk_error':
                raise OSError("Simulated disk I/O failure")
            else:  # timeout_error
                time.sleep(1)  # Brief pause
                raise TimeoutError("Simulated task timeout")
        
        # Execute requested tasks with better error handling
        try:
            if task_type in ['cpu', 'all']:
                print("\n=== Starting CPU Intensive Task ===")
                results['cpu_task'] = cpu_intensive_task(cpu_percent, cpu_duration)
        except Exception as e:
            print(f"CPU task failed: {e}")
            results['cpu_task'] = {
                "status": "error",
                "error": str(e),
                "task_type": "cpu"
            }
        
        try:
            if task_type in ['memory', 'all']:
                print("\n=== Starting Memory Intensive Task ===")
                results['memory_task'] = memory_intensive_task(memory_mb, memory_duration)
        except Exception as e:
            print(f"Memory task failed: {e}")
            results['memory_task'] = {
                "status": "error",
                "error": str(e),
                "task_type": "memory"
            }
        
        try:
            if task_type in ['disk', 'all']:
                print("\n=== Starting Disk Intensive Task ===")
                results['disk_task'] = disk_intensive_task(disk_mb, disk_duration)
        except Exception as e:
            print(f"Disk task failed: {e}")
            results['disk_task'] = {
                "status": "error",
                "error": str(e),
                "task_type": "disk"
            }
        
        total_time = time.time() - start_time
        
        print(f"\n=== Resource Test Complete ===")
        print(f"Total execution time: {total_time:.2f} seconds")
        
        result = {
            "status": "success",
            "task_type": task_type,
            "cpu_percent": cpu_percent,
            "cpu_duration_seconds": cpu_duration,
            "memory_mb": memory_mb,
            "memory_duration_seconds": memory_duration,
            "disk_mb": disk_mb,
            "disk_duration_seconds": disk_duration,
            "should_succeed": should_succeed,
            "failure_probability": failure_probability,
            "total_execution_time": total_time,
            "task_results": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_type": "resource_test",
            "note": "Uses Python standard library only for maximum compatibility"
        }
        
        return result
        
    except Exception as e:
        print(f"Critical error in resource test agent: {e}")
        error_result = {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "task_type": input_data.get('task_type', 'unknown') if 'input_data' in locals() else 'unknown',
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_type": "resource_test"
        }
        
        # Add available parameters if we have them
        if 'input_data' in locals():
            for param in ['cpu_percent', 'cpu_duration_seconds', 'memory_mb', 'memory_duration_seconds', 
                         'disk_mb', 'disk_duration_seconds', 'should_succeed', 'failure_probability']:
                if param in input_data:
                    error_result[param] = input_data[param]
        
        return error_result


if __name__ == "__main__":
    # Test with default parameters
    test_input = {
        "task_type": "all",
        "cpu_percent": 50,
        "cpu_duration_seconds": 10,
        "memory_mb": 50,
        "memory_duration_seconds": 10,
        "disk_mb": 25,
        "disk_duration_seconds": 10,
        "should_succeed": True,
        "failure_probability": 0.0
    }
    result = execute(test_input, {})
    print(f"\nTest result: {result}")
