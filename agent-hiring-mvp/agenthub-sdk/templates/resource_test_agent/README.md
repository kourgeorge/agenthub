# Resource Test Agent

A specialized agent designed to test Docker monitoring systems by performing CPU and memory intensive tasks. This agent is perfect for validating resource monitoring, alerting systems, and performance tracking in containerized environments.

## Purpose

The Resource Test Agent is specifically designed to:
- **Test Docker Monitoring**: Validate that your monitoring system correctly tracks CPU and memory usage
- **Stress Test Containers**: Ensure containers can handle resource-intensive workloads
- **Validate Resource Limits**: Test if resource limits and constraints are working properly
- **Performance Testing**: Measure how your system performs under various load conditions
- **Monitoring Calibration**: Help calibrate monitoring thresholds and alerting systems

## Implementation Notes

This agent is designed for **maximum compatibility** and uses **only Python standard library modules**:
- **No external dependencies** - works immediately in any Python environment
- **Docker-ready** - no package installation required
- **Cross-platform** - compatible with all Python installations
- **Resource efficient** - optimized for container environments

## Features

- **CPU Intensive Tasks**: Matrix operations, mathematical calculations, and iterative processing
- **Memory Intensive Tasks**: Large array allocation, data structure manipulation, and memory stress testing
- **Configurable Intensity**: Adjustable workload from light (level 1) to heavy (level 10)
- **Real-time Monitoring**: Tracks and reports resource usage during execution
- **Progress Tracking**: Provides real-time progress updates for long-running tasks
- **Resource Reporting**: Detailed reporting of CPU and memory consumption
- **Maximum Compatibility**: Uses only Python standard library modules for Docker compatibility

## Configuration

### Input Parameters

The agent accepts only two simple input parameters:

#### `task_type` (string)
- **Description**: Type of resource-intensive task to perform
- **Options**: 
  - `"cpu"` - Only CPU intensive tasks
  - `"memory"` - Only memory intensive tasks  
  - `"both"` - Both CPU and memory tasks (default)
- **Default**: `"both"`

#### `intensity` (integer)
- **Description**: Intensity level from 1 (low) to 10 (high)
- **Range**: 1-10
- **Default**: 5
- **Scaling**:
  - **CPU**: Each level adds ~1M iterations and 100x100 matrix operations
  - **Memory**: Each level adds ~100MB of memory allocation

## Usage Examples

### Basic Resource Testing
```json
{
  "task_type": "both",
  "intensity": 5
}
```

### CPU-Only Testing
```json
{
  "task_type": "cpu",
  "intensity": 7
}
```

### Memory-Only Testing
```json
{
  "task_type": "memory",
  "intensity": 3
}
```

### Light Load Testing
```json
{
  "task_type": "both",
  "intensity": 1
}
```

### Heavy Load Testing
```json
{
  "task_type": "both",
  "intensity": 10
}
```

## Output Format

The agent returns comprehensive resource usage information:

```json
{
  "status": "success",
  "task_type": "both",
  "intensity_level": 5,
  "total_execution_time": 45.2,
  "final_memory_mb": 512.3,
  "final_cpu_percent": 85.2,
  "task_results": {
    "cpu_task": {
      "task_type": "cpu",
      "iterations": 5000000,
      "matrix_size": 500,
      "execution_time": 25.1,
      "result_summary": "Processed 10 matrices of size 500x500"
    },
    "memory_task": {
      "task_type": "memory",
      "allocated_memory_mb": 500,
      "peak_memory_mb": 512.3,
      "execution_time": 20.1,
      "num_arrays_created": 500,
      "result_summary": "Allocated and processed 500MB of data"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_type": "resource_test"
}
```

## Resource Usage Patterns

### CPU Tasks
- **Matrix Operations**: Creates and manipulates large matrices
- **Mathematical Calculations**: Performs intensive mathematical operations
- **Iterative Processing**: Runs millions of iterations with progress tracking
- **Linear Algebra**: Matrix multiplication, inversion, and decomposition

### Memory Tasks
- **Array Allocation**: Creates large Python arrays and lists of various types
- **Data Structures**: Builds complex data structures in memory
- **Memory Stress**: Allocates memory in chunks to test memory management
- **Garbage Collection**: Tests memory cleanup and garbage collection

## Monitoring Integration

This agent is designed to work with various monitoring systems:

### Docker Metrics
- CPU usage percentage
- Memory usage (RSS)
- Execution time
- Resource allocation patterns

### Prometheus/Grafana
- Custom metrics for CPU and memory consumption
- Time-series data for resource usage
- Alerting thresholds based on intensity levels

### Container Orchestrators
- Kubernetes resource monitoring
- Docker Swarm metrics
- Resource limit validation

## Best Practices

### For Testing Monitoring Systems
1. **Start Light**: Begin with intensity level 1-3 to establish baselines
2. **Gradual Increase**: Test incrementally higher intensity levels
3. **Monitor Alerts**: Verify that monitoring systems trigger appropriate alerts
4. **Resource Limits**: Test against configured resource limits and constraints
5. **Baseline Comparison**: Compare results across different container configurations

### For Performance Testing
1. **Consistent Environment**: Run tests in the same container environment
2. **Multiple Runs**: Execute multiple test runs to account for variance
3. **Resource Monitoring**: Monitor both the agent and the host system
4. **Threshold Testing**: Test various intensity levels to find breaking points
5. **Cleanup Verification**: Ensure resources are properly released after execution

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce intensity level if you encounter memory allocation errors
2. **CPU Timeouts**: Lower intensity for environments with strict CPU time limits
3. **Container Crashes**: Check resource limits and adjust intensity accordingly
4. **Monitoring Gaps**: Verify that your monitoring system captures all metrics

### Performance Optimization

- **Intensity Scaling**: Use appropriate intensity levels for your environment
- **Resource Limits**: Set appropriate container resource limits
- **Monitoring Overhead**: Account for monitoring system overhead in measurements
- **Cleanup**: Ensure proper resource cleanup after testing

## Use Cases

### Development and Testing
- **CI/CD Pipelines**: Test resource monitoring in automated testing
- **Development Environments**: Validate monitoring setup during development
- **Staging Environments**: Test monitoring before production deployment

### Production Monitoring
- **Alert Validation**: Verify that monitoring alerts work correctly
- **Capacity Planning**: Understand resource usage patterns
- **Performance Baselines**: Establish performance benchmarks
- **Resource Optimization**: Identify resource usage optimization opportunities

### Compliance and Auditing
- **Resource Monitoring**: Validate that resource monitoring meets compliance requirements
- **Performance Audits**: Document system performance characteristics
- **Capacity Audits**: Verify resource allocation and usage tracking

## Security Considerations

- **Resource Limits**: Always set appropriate resource limits on containers
- **Monitoring Access**: Ensure monitoring systems have appropriate access controls
- **Data Handling**: The agent doesn't process sensitive data, but verify in your environment
- **Network Isolation**: Consider network isolation for testing environments

## License

MIT License - see LICENSE file for details.

## Support

For issues or questions related to this agent, please refer to the AgentHub documentation or contact the development team.
