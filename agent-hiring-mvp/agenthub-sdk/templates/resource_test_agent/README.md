# Resource Test Agent

A highly configurable agent designed to test Docker monitoring systems by performing CPU, memory, and disk intensive tasks with precise control over resource consumption and execution outcomes. This agent is perfect for validating resource monitoring, alerting systems, and performance tracking in containerized environments.

## Purpose

The Resource Test Agent is specifically designed to:
- **Test Docker Monitoring**: Validate that your monitoring system correctly tracks CPU, memory, and disk usage
- **Stress Test Containers**: Ensure containers can handle resource-intensive workloads
- **Validate Resource Limits**: Test if resource limits and constraints are working properly
- **Performance Testing**: Measure how your system performs under various load conditions
- **Monitoring Calibration**: Help calibrate monitoring thresholds and alerting systems
- **Failure Simulation**: Test error handling and monitoring systems under failure conditions
- **Resource Control**: Precisely control CPU usage, memory allocation, and disk I/O

## Implementation Notes

This agent is designed for **maximum compatibility** and uses **only Python standard library modules**:
- **No external dependencies** - works immediately in any Python environment
- **Docker-ready** - no package installation required
- **Cross-platform** - compatible with all Python installations
- **Resource efficient** - optimized for container environments
- **Configurable** - precise control over resource consumption and execution

## Features

- **CPU Intensive Tasks**: Configurable CPU usage percentage and duration with matrix operations and mathematical calculations
- **Memory Intensive Tasks**: Configurable memory allocation and duration with large array manipulation
- **Disk Intensive Tasks**: Configurable disk usage and duration with file I/O operations
- **Precise Resource Control**: Set exact CPU percentages, memory amounts, and disk usage
- **Duration Control**: Specify exact execution time for each resource type
- **Failure Simulation**: Control success/failure outcomes and failure probability
- **Real-time Monitoring**: Tracks and reports resource usage during execution
- **Progress Tracking**: Provides real-time progress updates for long-running tasks
- **Resource Reporting**: Detailed reporting of CPU, memory, and disk consumption
- **Maximum Compatibility**: Uses only Python standard library modules for Docker compatibility

## Configuration

### Input Parameters

The agent accepts comprehensive input parameters for precise resource control:

#### `task_type` (string)
- **Description**: Type of resource-intensive task to perform
- **Options**: 
  - `"cpu"` - Only CPU intensive tasks
  - `"memory"` - Only memory intensive tasks  
  - `"disk"` - Only disk intensive tasks
  - `"all"` - All resource types (default)
- **Default**: `"all"`

#### `cpu_percent` (integer)
- **Description**: Target CPU usage percentage during CPU intensive task
- **Range**: 1-100
- **Default**: 50
- **Usage**: Higher values create more CPU pressure, lower values create lighter load

#### `cpu_duration_seconds` (integer)
- **Description**: Duration for CPU intensive task in seconds
- **Range**: 1-3600 (max 1 hour)
- **Default**: 30
- **Usage**: Controls how long the CPU intensive task runs

#### `memory_mb` (integer)
- **Description**: Target memory usage in MB during memory intensive task
- **Range**: 1-10000 (max 10GB)
- **Default**: 100
- **Usage**: Higher values allocate more memory, lower values use less memory

#### `memory_duration_seconds` (integer)
- **Description**: Duration for memory intensive task in seconds
- **Range**: 1-3600 (max 1 hour)
- **Default**: 30
- **Usage**: Controls how long the memory intensive task runs

#### `disk_mb` (integer)
- **Description**: Target disk usage in MB during disk intensive task
- **Range**: 1-10000 (max 10GB)
- **Default**: 50
- **Usage**: Higher values create more files and disk I/O, lower values use less disk space

#### `disk_duration_seconds` (integer)
- **Description**: Duration for disk intensive task in seconds
- **Range**: 1-3600 (max 1 hour)
- **Default**: 30
- **Usage**: Controls how long the disk intensive task runs

#### `should_succeed` (boolean)
- **Description**: Whether the task should succeed (false to force failure)
- **Default**: true
- **Usage**: Set to false to test error handling and monitoring systems

#### `failure_probability` (number)
- **Description**: Probability of failure (0.0-1.0)
- **Range**: 0.0 (never fail) to 1.0 (always fail)
- **Default**: 0.0
- **Usage**: Use to test failure scenarios and error handling

## Usage Examples

### Basic Resource Testing
```json
{
  "task_type": "all",
  "cpu_percent": 50,
  "cpu_duration_seconds": 30,
  "memory_mb": 100,
  "memory_duration_seconds": 30,
  "disk_mb": 50,
  "disk_duration_seconds": 30
}
```

### CPU-Only Testing with High Load
```json
{
  "task_type": "cpu",
  "cpu_percent": 90,
  "cpu_duration_seconds": 60
}
```

### Memory-Only Testing with Large Allocation
```json
{
  "task_type": "memory",
  "memory_mb": 500,
  "memory_duration_seconds": 45
}
```

### Disk-Only Testing with Heavy I/O
```json
{
  "task_type": "disk",
  "disk_mb": 200,
  "disk_duration_seconds": 60
}
```

### Light Load Testing
```json
{
  "task_type": "all",
  "cpu_percent": 20,
  "cpu_duration_seconds": 15,
  "memory_mb": 25,
  "memory_duration_seconds": 15,
  "disk_mb": 10,
  "disk_duration_seconds": 15
}
```

### Heavy Load Testing
```json
{
  "task_type": "all",
  "cpu_percent": 95,
  "cpu_duration_seconds": 120,
  "memory_mb": 1000,
  "memory_duration_seconds": 120,
  "disk_mb": 500,
  "disk_duration_seconds": 120
}
```

### Failure Testing
```json
{
  "task_type": "all",
  "should_succeed": false,
  "failure_probability": 1.0
}
```

### Partial Failure Testing
```json
{
  "task_type": "all",
  "failure_probability": 0.3
}
```

## Output Format

The agent returns comprehensive resource usage information:

```json
{
  "status": "success",
  "task_type": "all",
  "cpu_percent": 50,
  "cpu_duration_seconds": 30,
  "memory_mb": 100,
  "memory_duration_seconds": 30,
  "disk_mb": 50,
  "disk_duration_seconds": 30,
  "should_succeed": true,
  "failure_probability": 0.0,
  "total_execution_time": 45.2,
  "task_results": {
    "cpu_task": {
      "task_type": "cpu",
      "target_cpu_percent": 50,
      "target_duration_seconds": 30,
      "actual_duration_seconds": 30.1,
      "iterations_completed": 1500,
      "matrix_size": 25,
      "execution_time": 30.1,
      "result_summary": "Processed 1500 iterations with 5 matrices of size 25x25"
    },
    "memory_task": {
      "task_type": "memory",
      "target_memory_mb": 100,
      "target_duration_seconds": 30,
      "actual_duration_seconds": 30.0,
      "allocated_memory_mb": 100,
      "estimated_memory_mb": 100.0,
      "execution_time": 30.0,
      "num_arrays_created": 100,
      "operations_completed": 3000,
      "result_summary": "Allocated and processed ~100MB of data for 30.0 seconds"
    },
    "disk_task": {
      "task_type": "disk",
      "target_disk_mb": 50,
      "target_duration_seconds": 30,
      "actual_duration_seconds": 30.0,
      "actual_disk_mb": 50,
      "files_created": 50,
      "read_operations": 1500,
      "execution_time": 30.0,
      "result_summary": "Created 50 files using 50MB of disk space for 30.0 seconds"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_type": "resource_test"
}
```

### Error Output Format

When failures occur, the agent provides detailed error information:

```json
{
  "status": "error",
  "error_message": "Simulated CPU task failure",
  "error_type": "RuntimeError",
  "task_type": "all",
  "cpu_percent": 50,
  "cpu_duration_seconds": 30,
  "memory_mb": 100,
  "memory_duration_seconds": 30,
  "disk_mb": 50,
  "disk_duration_seconds": 30,
  "should_succeed": false,
  "failure_probability": 1.0,
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_type": "resource_test"
}
```

## Resource Usage Patterns

### CPU Tasks
- **Matrix Operations**: Creates and manipulates large matrices based on CPU percentage
- **Mathematical Calculations**: Performs intensive mathematical operations scaled by target CPU usage
- **Iterative Processing**: Runs iterations until target duration is reached
- **Linear Algebra**: Matrix multiplication, inversion, and decomposition
- **Duration Control**: Precisely controls execution time regardless of CPU percentage

### Memory Tasks
- **Array Allocation**: Creates large Python arrays and lists of specified size
- **Data Structures**: Builds complex data structures in memory
- **Memory Stress**: Allocates memory in chunks to test memory management
- **Garbage Collection**: Tests memory cleanup and garbage collection
- **Duration Control**: Maintains memory allocation for specified duration

### Disk Tasks
- **File Creation**: Creates files of specified size until target disk usage is reached
- **I/O Operations**: Performs read/write operations for specified duration
- **Random Data**: Generates random data for realistic disk stress testing
- **Cleanup**: Automatically cleans up temporary files after testing
- **Duration Control**: Controls both write and read phases independently

## Monitoring Integration

This agent is designed to work with various monitoring systems:

### Docker Metrics
- CPU usage percentage (configurable)
- Memory usage (RSS) with precise control
- Disk I/O operations and usage
- Execution time with duration control

### Prometheus/Grafana
- Custom metrics for CPU, memory, and disk consumption
- Time-series data for resource usage
- Alerting thresholds based on configurable parameters
- Failure rate monitoring with configurable probability

### Container Orchestrators
- Kubernetes resource monitoring
- Docker Swarm metrics
- Resource limit validation with precise control

## Best Practices

### For Testing Monitoring Systems
1. **Start Light**: Begin with low CPU percentages and small memory/disk usage
2. **Gradual Increase**: Test incrementally higher resource consumption
3. **Duration Control**: Use short durations for initial testing, longer for stress testing
4. **Monitor Alerts**: Verify that monitoring systems trigger appropriate alerts
5. **Resource Limits**: Test against configured resource limits and constraints
6. **Failure Testing**: Test error handling with controlled failure scenarios

### For Performance Testing
1. **Consistent Environment**: Run tests in the same container environment
2. **Multiple Runs**: Execute multiple test runs to account for variance
3. **Resource Monitoring**: Monitor both the agent and the host system
4. **Threshold Testing**: Test various resource levels to find breaking points
5. **Cleanup Verification**: Ensure resources are properly released after execution
6. **Duration Planning**: Plan test durations based on your monitoring needs

### For Failure Testing
1. **Controlled Failures**: Use `should_succeed: false` for guaranteed failure testing
2. **Probability Testing**: Use `failure_probability` for realistic failure scenarios
3. **Error Type Variety**: Test different types of failures (CPU, memory, disk, timeout)
4. **Monitoring Validation**: Ensure monitoring systems capture and report failures
5. **Recovery Testing**: Test system recovery after simulated failures

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce `memory_mb` if you encounter memory allocation errors
2. **CPU Timeouts**: Lower `cpu_duration_seconds` for environments with strict CPU time limits
3. **Container Crashes**: Check resource limits and adjust parameters accordingly
4. **Monitoring Gaps**: Verify that your monitoring system captures all metrics
5. **Disk Space Issues**: Ensure sufficient disk space for `disk_mb` parameter
6. **Unexpected Failures**: Check `failure_probability` and `should_succeed` settings

### Performance Optimization

- **Resource Scaling**: Use appropriate resource levels for your environment
- **Duration Planning**: Set appropriate durations based on monitoring needs
- **Resource Limits**: Set appropriate container resource limits
- **Monitoring Overhead**: Account for monitoring system overhead in measurements
- **Cleanup**: Ensure proper resource cleanup after testing

## Use Cases

### Development and Testing
- **CI/CD Pipelines**: Test resource monitoring in automated testing
- **Development Environments**: Validate monitoring setup during development
- **Staging Environments**: Test monitoring before production deployment
- **Failure Simulation**: Test error handling and monitoring under failure conditions

### Production Monitoring
- **Alert Validation**: Verify that monitoring alerts work correctly
- **Capacity Planning**: Understand resource usage patterns with precise control
- **Performance Baselines**: Establish performance benchmarks
- **Resource Optimization**: Identify resource usage optimization opportunities
- **Failure Response**: Test monitoring and alerting under failure scenarios

### Compliance and Auditing
- **Resource Monitoring**: Validate that resource monitoring meets compliance requirements
- **Performance Audits**: Document system performance characteristics
- **Capacity Audits**: Verify resource allocation and usage tracking
- **Failure Handling**: Document error handling and recovery procedures

## Security Considerations

- **Resource Limits**: Always set appropriate resource limits on containers
- **Monitoring Access**: Ensure monitoring systems have appropriate access controls
- **Data Handling**: The agent doesn't process sensitive data, but verify in your environment
- **Network Isolation**: Consider network isolation for testing environments
- **Temporary Files**: Disk testing creates temporary files that are automatically cleaned up

## License

MIT License - see LICENSE file for details.

## Support

For issues or questions related to this agent, please refer to the AgentHub documentation or contact the development team.
