# AgentHub Prometheus Monitoring

This document explains how to set up and use Prometheus monitoring for your AgentHub Docker containers.

## 🎯 Overview

The monitoring system provides:
- **Real-time container metrics** (CPU, memory, network, disk I/O)
- **Agent execution statistics** (success/failure rates, duration)
- **System-wide container counts** by deployment type
- **Historical data visualization** through Grafana dashboards
- **Prometheus-compatible metrics** for external monitoring tools

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install the prometheus-client Python package
pip install prometheus-client

# Or install all requirements
pip install -r requirements.txt
```

### 2. Start the Monitoring Stack

```bash
# Use the automated setup script
./setup_monitoring.sh

# Or manually start with Docker Compose
docker-compose -f docker-compose.monitoring.yml up -d
```

### 3. Access Your Monitoring Tools

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Node Exporter**: http://localhost:9100

## 📊 Available Metrics

### Container Metrics

| Metric | Description | Labels |
|--------|-------------|---------|
| `container_cpu_usage_percent` | CPU usage percentage | container_name, agent_id, hiring_id, deployment_type |
| `container_memory_usage_bytes` | Memory usage in bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_memory_limit_bytes` | Memory limit in bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_network_rx_bytes` | Network received bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_network_tx_bytes` | Network transmitted bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_block_read_bytes` | Block read bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_block_write_bytes` | Block write bytes | container_name, agent_id, hiring_id, deployment_type |
| `container_status` | Container status (1=running, 0=stopped) | container_name, agent_id, hiring_id, deployment_type |

### System Metrics

| Metric | Description | Labels |
|--------|-------------|---------|
| `total_containers` | Total container count | deployment_type |
| `running_containers` | Running container count | deployment_type |
| `stopped_containers` | Stopped container count | deployment_type |

### Execution Metrics

| Metric | Description | Labels |
|--------|-------------|---------|
| `agent_execution_duration_seconds` | Execution duration histogram | agent_id, deployment_type |
| `agent_execution_success_total` | Successful execution count | agent_id, deployment_type |
| `agent_execution_failure_total` | Failed execution count | agent_id, deployment_type |

## 🔧 Configuration

### Prometheus Configuration

The `prometheus.yml` file configures what metrics to scrape:

```yaml
scrape_configs:
  - job_name: 'agenthub-api'
    static_configs:
      - targets: ['localhost:8000']  # Your API server
    metrics_path: '/api/v1/metrics/prometheus'
    scrape_interval: 30s
```

### Environment Variables

You can configure the monitoring system with these environment variables:

```bash
# Metrics collection interval (seconds)
AGENTHUB_METRICS_INTERVAL=30

# Metrics retention (hours)
AGENTHUB_METRICS_RETENTION=24

# Enable debug logging
AGENTHUB_METRICS_DEBUG=true
```

## 📈 Using Grafana Dashboards

### Pre-configured Dashboard

The system includes a pre-configured dashboard with:
- Container CPU and memory usage
- Network I/O metrics
- Block I/O metrics
- Container count statistics
- Execution success rates

### Custom Dashboards

Create custom dashboards using these example queries:

```promql
# CPU usage for specific agent type
container_cpu_usage_percent{deployment_type="acp"}

# Memory usage trend
rate(container_memory_usage_bytes[5m])

# Container count by type
running_containers{deployment_type=~"acp|function|persistent"}

# Execution success rate
rate(agent_execution_success_total[5m]) / (rate(agent_execution_success_total[5m]) + rate(agent_execution_failure_total[5m]))
```

## 🔍 API Endpoints

### Metrics Endpoints

| Endpoint | Description | Response Format |
|----------|-------------|-----------------|
| `/api/v1/metrics/prometheus` | Prometheus metrics | text/plain |
| `/api/v1/metrics/containers` | Container metrics summary | JSON |
| `/api/v1/metrics/containers/{deployment_id}` | Specific container metrics | JSON |
| `/api/v1/metrics/system` | System-wide metrics | JSON |
| `/api/v1/metrics/collect` | Trigger metrics collection | JSON |

### Example Usage

```bash
# Get Prometheus metrics
curl http://localhost:8000/api/v1/metrics/prometheus

# Get container summary
curl http://localhost:8000/api/v1/metrics/containers

# Trigger metrics collection
curl -X POST http://localhost:8000/api/v1/metrics/collect
```

## 🐳 Docker Integration

### Container Naming Convention

The system automatically detects container types based on naming:

- `acp-*` → ACP server agents
- `func-*` → Function agents  
- `persis-*` → Persistent agents

### Resource Limits Monitoring

The system tracks resource limits and usage:

```bash
# View container resource limits
docker inspect <container_name> --format='{{.HostConfig.Memory}} {{.HostConfig.CpuQuota}}'

# Compare with actual usage
curl http://localhost:8000/api/v1/metrics/containers
```

## 🔄 Automation

### Scheduled Metrics Collection

The system automatically collects metrics when:
- Containers start/stop
- API endpoints are called
- Health checks run

### Manual Collection

Trigger manual collection:

```bash
# Collect all metrics
curl -X POST http://localhost:8000/api/v1/metrics/collect

# Collect specific container
curl -X POST http://localhost:8000/api/v1/metrics/containers/{deployment_id}
```

## 🚨 Alerts and Notifications

### Built-in Alerts

The system includes basic alerting for:
- High CPU usage (>80%)
- High memory usage (>90%)
- Container crashes
- Failed health checks

### Custom Alerts

Create custom alerts in Prometheus:

```yaml
groups:
  - name: agenthub_alerts
    rules:
      - alert: HighCPUUsage
        expr: container_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.container_name }}"
          description: "Container {{ $labels.container_name }} has high CPU usage: {{ $value }}%"
```

## 🧹 Maintenance

### Cleanup Old Metrics

```bash
# Clean up metrics older than 24 hours
curl -X POST "http://localhost:8000/api/v1/metrics/cleanup?max_age_hours=24"

# Or use the API endpoint
curl -X POST http://localhost:8000/api/v1/metrics/cleanup
```

### Data Retention

- **Prometheus**: 200 hours (configurable in docker-compose)
- **Grafana**: Persistent (stored in Docker volumes)
- **Application metrics**: 24 hours (configurable)

## 🔧 Troubleshooting

### Common Issues

1. **Metrics not showing up**
   - Check if containers are running
   - Verify API server is accessible
   - Check Prometheus targets status

2. **High resource usage**
   - Monitor the monitoring stack itself
   - Adjust scrape intervals
   - Use sampling for high-frequency metrics

3. **Dashboard not loading**
   - Verify Prometheus datasource in Grafana
   - Check dashboard JSON syntax
   - Restart Grafana container

### Debug Mode

Enable debug logging:

```bash
export AGENTHUB_METRICS_DEBUG=true
# Restart your API server
```

### Health Checks

```bash
# Check Prometheus health
curl http://localhost:9090/-/healthy

# Check Grafana health
curl http://localhost:3000/api/health

# Check API metrics endpoint
curl http://localhost:8000/api/v1/metrics/prometheus
```

## 📚 Advanced Usage

### Custom Metrics

Add custom metrics to your agents:

```python
from prometheus_client import Counter, Histogram

# Custom metrics
request_counter = Counter('agent_requests_total', 'Total requests', ['agent_id'])
request_duration = Histogram('agent_request_duration_seconds', 'Request duration')

# Record metrics
request_counter.labels(agent_id='my_agent').inc()
request_duration.observe(0.5)
```

### External Monitoring

Integrate with external monitoring systems:

```bash
# Send metrics to external Prometheus
curl -X POST http://external-prometheus:9090/api/v1/write \
  -d "$(curl -s http://localhost:8000/api/v1/metrics/prometheus)"

# Use as data source for other tools
# Grafana, Kibana, etc.
```

## 🤝 Contributing

To add new metrics:

1. Extend the `PrometheusMetricsService` class
2. Add new metric definitions in `_init_metrics()`
3. Update the collection methods
4. Add corresponding API endpoints
5. Update the Grafana dashboard

## 📞 Support

For issues with the monitoring system:

1. Check the logs: `docker-compose -f docker-compose.monitoring.yml logs`
2. Verify configuration files
3. Check network connectivity between services
4. Review Prometheus target status

## 🔗 Useful Links

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Docker Metrics](https://docs.docker.com/config/daemon/prometheus/)
