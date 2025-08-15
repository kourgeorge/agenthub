# AgentHub Enhanced Billing System

This document explains the enhanced billing system that provides **AWS EC2-style hourly billing** for agent deployments based on actual resource consumption.

## 🎯 Overview

The enhanced billing system tracks **real-time container resource usage** and calculates costs based on:
- **CPU usage** (proportional to actual consumption)
- **Memory usage** (based on actual RAM consumption)
- **Network I/O** (data transfer costs)
- **Storage allocation** (based on memory limits)
- **Container status** (running vs suspended)

## 💰 Billing Model

### **AWS EC2-Style Hourly Billing**

Unlike traditional per-request billing, this system charges based on **actual resource consumption over time**:

```
Cost = (CPU Usage % × CPU Cost/Hour × Time) + (Memory GB × Memory Cost/GB-Hour × Time) + Network + Storage
```

**Example:**
- Container runs for 2 hours
- Average CPU: 30% (0.3 × $0.0416/hour × 2 hours = $0.025)
- Average Memory: 1GB (1GB × $0.0056/GB-hour × 2 hours = $0.0112)
- **Total: $0.0362 for 2 hours**

### **Resource Pricing (AWS-Competitive)**

| Resource | ACP Agents | Function Agents | Persistent Agents |
|----------|------------|-----------------|-------------------|
| **CPU** | $0.0416/hour | $0.0208/hour | $0.0312/hour |
| **Memory** | $0.0056/GB-hour | $0.0028/GB-hour | $0.0042/GB-hour |
| **Network** | $0.09/GB | $0.09/GB | $0.09/GB |
| **Storage** | $0.10/GB-month | $0.10/GB-month | $0.10/GB-month |

*Prices are configurable and based on AWS EC2 t3 instance pricing*

## 🔄 How It Works

### **1. Real-Time Monitoring**

The system collects metrics every **30 seconds** for accurate hourly billing:

```
Time: 10:00:00 → Container uses 25% CPU, 512MB RAM → Cost: $0.0023
Time: 10:00:30 → Container uses 45% CPU, 768MB RAM → Cost: $0.0041
Time: 10:01:00 → Container uses 12% CPU, 256MB RAM → Cost: $0.0012
```

### **2. Cost Calculation**

Each 30-second snapshot calculates costs:

```python
# CPU cost: proportional to usage percentage
cpu_cost = (cpu_usage_percent / 100.0) * cpu_cost_per_hour * (30/3600)

# Memory cost: based on actual usage
memory_cost = memory_gb * memory_cost_per_gb_hour * (30/3600)

# Network cost: based on data transfer
network_cost = network_gb * network_cost_per_gb

# Storage cost: based on allocated memory
storage_cost = memory_limit_gb * storage_cost_per_gb_hour * (30/3600)
```

### **3. Hourly Aggregation**

Every hour, the system aggregates 30-second snapshots:

```
Hour 10:00-11:00:
- 120 snapshots (30 seconds each)
- Total cost: $0.0076
- Average CPU: 27.3%
- Average Memory: 0.51GB
- Network: 0.5GB
```

### **4. Daily Aggregation**

Daily reports provide comprehensive usage summaries:

```
Date: 2024-01-15
- Total cost: $0.1824
- CPU hours: 6.55
- Memory GB-hours: 12.24
- Network: 12.0GB
- Requests: 150
```

### **5. Monthly Billing**

Monthly billing aggregates daily totals for final invoices.

## 📊 API Endpoints

### **Enhanced Billing Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/enhanced-billing/summary/{user_id}` | GET | Comprehensive billing summary |
| `/api/v1/enhanced-billing/daily-usage/{user_id}` | GET | Detailed daily usage |
| `/api/v1/enhanced-billing/cost-estimate` | POST | Deployment cost estimation |
| `/api/v1/enhanced-billing/budget-check/{user_id}` | GET | Budget limit checking |
| `/api/v1/enhanced-billing/monthly-breakdown/{user_id}` | GET | Monthly cost breakdown |
| `/api/v1/enhanced-billing/deployment-costs/{deployment_id}` | GET | Individual deployment costs |
| `/api/v1/enhanced-billing/pricing` | GET | Current resource pricing |

### **Example Usage**

#### **Get User Billing Summary**
```bash
curl "http://localhost:8000/api/v1/enhanced-billing/summary/123?months=3"
```

**Response:**
```json
{
  "user_id": 123,
  "username": "john_doe",
  "billing_period": {
    "start": "2024-10-15T00:00:00+00:00",
    "end": "2025-01-15T00:00:00+00:00",
    "months": 3
  },
  "cost_summary": {
    "total_cost": 15.67,
    "container_resource_cost": 12.45,
    "execution_cost": 3.22,
    "currency": "USD"
  },
  "resource_usage": {
    "total_cpu_hours": 45.2,
    "total_memory_gb_hours": 89.6,
    "total_network_gb": 156.8,
    "total_deployments": 5,
    "total_requests": 1250
  },
  "deployment_breakdown": [...],
  "monthly_breakdown": [...],
  "budget": {
    "monthly_budget": 50.0,
    "current_usage": 15.67,
    "remaining_budget": 34.33,
    "utilization_percent": 31.34
  }
}
```

#### **Get Cost Estimate**
```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-billing/cost-estimate" \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_type": "acp",
    "duration_hours": 24,
    "avg_cpu_percent": 50.0,
    "avg_memory_gb": 2.0
  }'
```

**Response:**
```json
{
  "deployment_type": "acp",
  "duration_hours": 24,
  "estimated_costs": {
    "cpu_cost": 0.4992,
    "memory_cost": 0.2688,
    "storage_cost": 0.0066,
    "total_cost": 0.7746,
    "cost_per_hour": 0.0323
  },
  "assumptions": {
    "avg_cpu_percent": 50.0,
    "avg_memory_gb": 2.0,
    "pricing_model": "AWS-competitive hourly rates"
  },
  "currency": "USD"
}
```

## 🐳 Container Status Billing

### **Running Containers**
- **Full billing**: CPU, memory, network, storage
- **Real-time monitoring**: Every 30 seconds
- **Accurate costs**: Based on actual resource consumption

### **Suspended Containers**
- **Storage only**: Memory allocation costs
- **No compute costs**: CPU and memory usage not charged
- **Network costs**: Only if data transfer occurs

**Example:**
```
Running container (1 hour): $0.0416 (CPU) + $0.0056 (Memory) = $0.0472
Suspended container (1 hour): $0.0001 (Storage only) = $0.0001
```

## 📈 Cost Optimization

### **Resource Efficiency**
- **Idle containers**: Minimal costs (storage only)
- **Active containers**: Proportional to actual usage
- **Resource limits**: Prevent runaway costs

### **Deployment Strategies**
- **Function agents**: Best for short, infrequent tasks
- **ACP agents**: Good for continuous, moderate usage
- **Persistent agents**: Ideal for long-running, active services

### **Cost Monitoring**
- **Real-time tracking**: Monitor costs as they occur
- **Budget alerts**: Prevent unexpected charges
- **Usage analytics**: Identify optimization opportunities

## 🔧 Configuration

### **Environment Variables**

```bash
# Resource pricing (override defaults)
AGENTHUB_CPU_COST_ACP=0.0416
AGENTHUB_CPU_COST_FUNCTION=0.0208
AGENTHUB_CPU_COST_PERSISTENT=0.0312

AGENTHUB_MEMORY_COST_ACP=0.0056
AGENTHUB_MEMORY_COST_FUNCTION=0.0028
AGENTHUB_MEMORY_COST_PERSISTENT=0.0042

# Collection interval
AGENTHUB_METRICS_INTERVAL=30

# Cost calculation precision
AGENTHUB_COST_PRECISION=6
```

### **Database Configuration**

The system automatically creates pricing records in the `resource_pricing` table:

```sql
INSERT INTO resource_pricing (
    resource_type, deployment_type, base_price, price_unit, currency
) VALUES 
('cpu', 'acp', 0.0416, 'per_hour', 'USD'),
('cpu', 'function', 0.0208, 'per_hour', 'USD'),
('cpu', 'persistent', 0.0312, 'per_hour', 'USD'),
('memory', 'acp', 0.0056, 'per_gb_hour', 'USD'),
('memory', 'function', 0.0028, 'per_gb_hour', 'USD'),
('memory', 'persistent', 0.0042, 'per_gb_hour', 'USD');
```

## 📊 Reporting and Analytics

### **Daily Reports**
- **Resource usage**: CPU, memory, network consumption
- **Cost breakdown**: By resource type and deployment
- **Activity metrics**: Request counts and performance
- **Hourly breakdown**: 24-hour usage patterns

### **Monthly Reports**
- **Cost trends**: Month-over-month changes
- **Deployment analysis**: Most/least expensive agents
- **Budget utilization**: Spending vs. limits
- **Projections**: Estimated future costs

### **Real-Time Monitoring**
- **Live costs**: Current session expenses
- **Resource alerts**: High usage notifications
- **Budget warnings**: Approaching limits
- **Performance metrics**: Response times and success rates

## 🚀 Getting Started

### **1. Enable Enhanced Billing**

```bash
# Install dependencies
pip install prometheus-client

# Start monitoring stack
./setup_monitoring.sh
```

### **2. Deploy Your First Agent**

```bash
# Hire an agent
agenthub hire agent <agent_id>

# Check cost estimate
curl -X POST "http://localhost:8000/api/v1/enhanced-billing/cost-estimate" \
  -H "Content-Type: application/json" \
  -d '{"deployment_type": "acp", "duration_hours": 1, "avg_cpu_percent": 30, "avg_memory_gb": 1}'
```

### **3. Monitor Usage**

```bash
# Get real-time billing
curl "http://localhost:8000/api/v1/enhanced-billing/summary/123"

# Check daily usage
curl "http://localhost:8000/api/v1/enhanced-billing/daily-usage/123?date=2024-01-15"
```

### **4. View in Grafana**

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Pre-configured dashboard**: AgentHub Container Metrics

## 🔍 Troubleshooting

### **Common Issues**

1. **No metrics appearing**
   - Check if containers are running
   - Verify Prometheus can scrape metrics
   - Check collection interval settings

2. **Incorrect costs**
   - Verify pricing configuration
   - Check resource limits
   - Review container status

3. **High costs**
   - Monitor resource usage
   - Check for resource leaks
   - Optimize agent configurations

### **Debug Mode**

```bash
export AGENTHUB_METRICS_DEBUG=true
export AGENTHUB_BILLING_DEBUG=true
# Restart your API server
```

### **Health Checks**

```bash
# Check metrics endpoint
curl "http://localhost:8000/api/v1/metrics/prometheus"

# Check billing endpoint
curl "http://localhost:8000/api/v1/enhanced-billing/pricing"
```

## 💡 Best Practices

### **Cost Optimization**
1. **Use appropriate agent types** for your workload
2. **Monitor resource usage** regularly
3. **Set resource limits** to prevent runaway costs
4. **Suspend unused agents** to minimize charges

### **Monitoring Setup**
1. **Set up alerts** for high usage
2. **Configure budgets** to prevent overspending
3. **Review daily reports** for anomalies
4. **Use cost estimates** before deployments

### **Resource Management**
1. **Right-size containers** for your workload
2. **Monitor memory usage** to optimize allocation
3. **Track network costs** for data-heavy operations
4. **Regular cleanup** of unused resources

## 🔮 Future Enhancements

### **Planned Features**
- **Predictive billing**: AI-powered cost forecasting
- **Auto-scaling**: Automatic resource optimization
- **Cost alerts**: Real-time spending notifications
- **Usage analytics**: Advanced reporting and insights
- **Multi-currency**: Support for different currencies
- **Tiered pricing**: Volume discounts and enterprise rates

### **Integration Opportunities**
- **LiteLLM**: Accurate token-based billing
- **External monitoring**: Integration with existing tools
- **Billing providers**: Stripe, PayPal integration
- **Accounting systems**: QuickBooks, Xero integration

## 📞 Support

For issues with the enhanced billing system:

1. **Check logs**: `docker-compose -f docker-compose.monitoring.yml logs`
2. **Verify metrics**: Check Prometheus targets
3. **Review configuration**: Verify pricing and intervals
4. **Test endpoints**: Use the test script

## 🔗 Related Documentation

- [Prometheus Monitoring Setup](MONITORING_README.md)
- [Resource Limits Configuration](documentation/RESOURCE_LIMITS_README.md)
- [API Reference](documentation/CLI_REFERENCE.md)
- [Database Schema](documentation/DATABASE_SCHEMA.md)

---

This enhanced billing system provides **transparent, fair, and accurate** cost tracking for your AgentHub deployments, giving users complete visibility into their resource consumption and costs.
