# AgentHub Resource Limits System

This document explains how to configure and use the resource limits system for Docker containers in AgentHub.

## 🎯 Overview

The resource limits system provides:
- **Default memory and CPU limits** for all agent containers
- **Agent-specific overrides** through configuration files
- **Environment variable configuration** for system-wide defaults
- **Safety caps** to prevent resource exhaustion
- **Automatic validation** of resource specifications

## 🚀 Quick Start

### 1. Enable Resource Limits

Resource limits are automatically applied to new containers. No code changes needed!

### 2. Configure Defaults (Optional)

Copy the example environment file and modify as needed:

```bash
cp env-resource-limits-example.txt .env
```

### 3. Test the System

Run the test script to verify everything works:

```bash
python3 test_resource_limits.py
```

## ⚙️ Configuration Options

### Environment Variables

Set these in your `.env` file to override system defaults:

```bash
# Default resource limits
AGENTHUB_DEFAULT_MEMORY_LIMIT=512m
AGENTHUB_DEFAULT_MEMORY_SWAP=1g
AGENTHUB_DEFAULT_CPU_LIMIT=1.0
AGENTHUB_DEFAULT_PIDS_LIMIT=100

# Maximum safety caps
AGENTHUB_MAX_MEMORY_LIMIT=4g
AGENTHUB_MAX_MEMORY_SWAP=8g
AGENTHUB_MAX_CPU_LIMIT=4.0
AGENTHUB_MAX_PIDS_LIMIT=500
```

### Agent-Specific Overrides

Agents can override system defaults in their `config.json`:

```json
{
  "deployment": {
    "resources": {
      "memory_limit": "2GB",
      "cpu_limit": "2.0",
      "memory_swap": "4GB",
      "pids_limit": 200
    }
  }
}
```

## 📊 Default Resource Limits

### By Agent Type

| Agent Type | Memory | CPU | PIDs | Use Case |
|------------|--------|-----|------|----------|
| **Function** | 256m | 0.5 cores | 50 | Simple functions, echo agents |
| **ACP Server** | 1g | 1.0 cores | 100 | Web services, API endpoints |
| **Persistent** | 512m | 0.75 cores | 75 | Stateful agents, RAG systems |

### Memory Format Examples

- `256m` = 256 megabytes
- `1g` = 1 gigabyte
- `2GB` = 2 gigabytes (case insensitive)

### CPU Format Examples

- `0.5` = Half a CPU core
- `1.0` = One full CPU core
- `2.5` = Two and a half CPU cores

## 🔧 Implementation Details

### Files Modified

1. **`server/services/resource_limits.py`** - Core resource limits system
2. **`server/services/deployment_service.py`** - ACP agent deployment
3. **`server/services/function_deployment_service.py`** - Function agent deployment

### How It Works

1. **Container Creation**: When deploying a container, the system:
   - Gets default limits for the agent type
   - Checks for agent-specific overrides
   - Applies safety caps
   - Converts to Docker configuration

2. **Resource Validation**: All limits are validated:
   - Memory format (e.g., "512m", "1g")
   - CPU limits (0.1 to MAX_CPU)
   - Process limits (1 to MAX_PIDS)

3. **Docker Integration**: Limits are converted to Docker parameters:
   - `mem_limit` - Memory limit
   - `memswap_limit` - Memory + swap limit
   - `cpu_quota` - CPU time limit
   - `pids_limit` - Process limit

## 📝 Usage Examples

### Basic Function Agent

```json
{
  "name": "Simple Echo Agent",
  "agent_type": "function",
  "deployment": {
    "resources": {
      "memory_limit": "128m",
      "cpu_limit": "0.25"
    }
  }
}
```

### Heavy ML Agent

```json
{
  "name": "ML Processing Agent",
  "agent_type": "acp_server",
  "deployment": {
    "resources": {
      "memory_limit": "4GB",
      "cpu_limit": "3.0",
      "memory_swap": "8GB",
      "pids_limit": 300
    }
  }
}
```

### RAG Agent

```json
{
  "name": "Document RAG Agent",
  "agent_type": "persistent",
  "deployment": {
    "resources": {
      "memory_limit": "2GB",
      "cpu_limit": "1.5",
      "memory_swap": "4GB"
    }
  }
}
```

## 🧪 Testing

### Run Tests

```bash
python3 test_resource_limits.py
```

### Test Specific Scenarios

```python
from server.services.resource_limits import get_agent_resource_limits

# Test agent with custom limits
agent_config = {
    "deployment": {
        "resources": {
            "memory_limit": "1GB",
            "cpu_limit": "2.0"
        }
    }
}

limits = get_agent_resource_limits(agent_config, "function")
print(f"Memory: {limits.memory_limit}")
print(f"CPU: {limits.cpu_limit}")
```

## 🔍 Monitoring

### Check Container Limits

```bash
# View resource limits for running containers
docker inspect <container_name> --format='{{.HostConfig.Memory}} {{.HostConfig.CpuQuota}}'

# Monitor resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Resource Usage Dashboard

The system automatically tracks:
- Memory usage per container
- CPU usage per container
- Process count per container
- Resource limit violations

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**: Check memory limits aren't too low
2. **Agent runs slowly**: CPU limits might be too restrictive
3. **Out of memory errors**: Increase memory limits or check for memory leaks

### Debug Mode

Enable detailed logging:

```bash
export AGENTHUB_LOG_LEVEL=DEBUG
```

### Reset to Defaults

Remove environment variables to use hardcoded defaults:

```bash
unset AGENTHUB_DEFAULT_MEMORY_LIMIT
unset AGENTHUB_DEFAULT_CPU_LIMIT
```

## 📚 API Reference

### ResourceLimits Class

```python
@dataclass
class ResourceLimits:
    memory_limit: str      # Memory limit (e.g., "512m")
    memory_swap: str       # Memory + swap limit
    cpu_limit: str         # CPU limit (e.g., "1.0")
    pids_limit: int        # Process limit
    ulimits: Optional[Dict[str, int]] = None
```

### Main Functions

- `get_agent_resource_limits(agent_config, agent_type)` - Get limits for agent
- `get_default_limits(agent_type)` - Get default limits for agent type
- `to_docker_config(limits)` - Convert to Docker configuration
- `get_resource_summary()` - Get system configuration summary

## 🔒 Security Considerations

### Resource Exhaustion Protection

- **Safety caps** prevent agents from requesting excessive resources
- **Validation** ensures all limits are within acceptable ranges
- **Defaults** provide reasonable limits for all agent types

### Isolation

- Each container has its own resource limits
- Agents cannot access resources beyond their limits
- System resources are protected from runaway agents

## 🚀 Future Enhancements

### Planned Features

1. **Dynamic scaling** based on usage patterns
2. **Resource quotas** per user/organization
3. **Automatic optimization** of resource allocation
4. **Resource usage analytics** and reporting

### Contributing

To add new resource limit types or modify the system:

1. Update `ResourceLimits` dataclass
2. Add validation methods
3. Update Docker configuration conversion
4. Add tests
5. Update documentation

## 📞 Support

For questions or issues with the resource limits system:

1. Check the test script output
2. Review environment variable configuration
3. Check Docker container logs
4. Verify agent configuration files

---

**Note**: Resource limits are applied to new containers only. Existing containers will continue to run without limits until redeployed.
