"""Prometheus metrics service for monitoring Docker containers and system resources."""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import docker
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, 
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)

logger = logging.getLogger(__name__)


class PrometheusMetricsService:
    """Service for collecting and exposing Prometheus metrics for Docker containers."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.registry = CollectorRegistry()
        
        # Initialize metrics
        self._init_metrics()
        
        # Track container metrics
        self.container_metrics = {}
        
    def _init_metrics(self):
        """Initialize Prometheus metrics."""
        
        # Container metrics
        self.container_cpu_usage = Gauge(
            'container_cpu_usage_percent',
            'CPU usage percentage per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_memory_usage = Gauge(
            'container_memory_usage_bytes',
            'Memory usage in bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_memory_limit = Gauge(
            'container_memory_limit_bytes',
            'Memory limit in bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_network_rx = Gauge(
            'container_network_rx_bytes',
            'Network received bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_network_tx = Gauge(
            'container_network_tx_bytes',
            'Network transmitted bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_block_read = Gauge(
            'container_block_read_bytes',
            'Block read bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_block_write = Gauge(
            'container_block_write_bytes',
            'Block write bytes per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        # Container status metrics
        self.container_status = Gauge(
            'container_status',
            'Container status (1=running, 0=stopped/other)',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.container_restart_count = Counter(
            'container_restart_count_total',
            'Total restart count per container',
            ['container_name', 'agent_id', 'hiring_id', 'deployment_type'],
            registry=self.registry
        )
        
        # System metrics
        self.total_containers = Gauge(
            'total_containers',
            'Total number of containers',
            ['deployment_type'],
            registry=self.registry
        )
        
        self.running_containers = Gauge(
            'running_containers',
            'Number of running containers',
            ['deployment_type'],
            registry=self.registry
        )
        
        self.stopped_containers = Gauge(
            'stopped_containers',
            'Number of stopped containers',
            ['deployment_type'],
            registry=self.registry
        )
        
        # Resource usage histograms
        self.cpu_usage_histogram = Histogram(
            'container_cpu_usage_histogram',
            'CPU usage distribution',
            ['deployment_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0],
            registry=self.registry
        )
        
        self.memory_usage_histogram = Histogram(
            'container_memory_usage_histogram',
            'Memory usage distribution in bytes',
            ['deployment_type'],
            buckets=[1024*1024, 10*1024*1024, 100*1024*1024, 1024*1024*1024, 2*1024*1024*1024],
            registry=self.registry
        )
        
        # Execution metrics
        self.execution_duration = Histogram(
            'agent_execution_duration_seconds',
            'Agent execution duration in seconds',
            ['agent_id', 'deployment_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        self.execution_success = Counter(
            'agent_execution_success_total',
            'Total successful executions',
            ['agent_id', 'deployment_type'],
            registry=self.registry
        )
        
        self.execution_failure = Counter(
            'agent_execution_failure_total',
            'Total failed executions',
            ['agent_id', 'deployment_type'],
            registry=self.registry
        )
    
    def collect_container_metrics(self, deployment_info: Dict[str, Any]):
        """Collect metrics for a specific container deployment."""
        try:
            container_name = deployment_info.get('container_name')
            if not container_name:
                return
            
            # Get container stats
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            # Extract container info
            agent_id = deployment_info.get('agent_id', 'unknown')
            hiring_id = deployment_info.get('hiring_id', 'unknown')
            deployment_type = deployment_info.get('deployment_type', 'unknown')
            
            # Calculate CPU usage percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_usage_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            # Network stats
            network_stats = stats['networks']
            rx_bytes = sum(net['rx_bytes'] for net in network_stats.values()) if network_stats else 0
            tx_bytes = sum(net['tx_bytes'] for net in network_stats.values()) if network_stats else 0
            
            # Block I/O stats
            block_stats = stats['blkio_stats']['io_service_bytes']
            read_bytes = sum(stat['value'] for stat in block_stats if stat['op'] == 'Read')
            write_bytes = sum(stat['value'] for stat in block_stats if stat['op'] == 'Write')
            
            # Update metrics
            self.container_cpu_usage.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(cpu_usage_percent)
            
            self.container_memory_usage.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(memory_usage)
            
            self.container_memory_limit.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(memory_limit)
            
            self.container_network_rx.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(rx_bytes)
            
            self.container_network_tx.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(tx_bytes)
            
            self.container_block_read.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(read_bytes)
            
            self.container_block_write.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(write_bytes)
            
            # Container status
            status_value = 1 if container.status == 'running' else 0
            self.container_status.labels(
                container_name=container_name,
                agent_id=agent_id,
                hiring_id=hiring_id,
                deployment_type=deployment_type
            ).set(status_value)
            
            # Update histograms
            self.cpu_usage_histogram.labels(deployment_type=deployment_type).observe(cpu_usage_percent)
            self.memory_usage_histogram.labels(deployment_type=deployment_type).observe(memory_usage)
            
            # Store metrics for later reference
            self.container_metrics[container_name] = {
                'cpu_usage': cpu_usage_percent,
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'network_rx': rx_bytes,
                'network_tx': tx_bytes,
                'block_read': read_bytes,
                'block_write': write_bytes,
                'status': container.status,
                'last_updated': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics for container {container_name}: {e}")
    
    def collect_system_metrics(self):
        """Collect system-wide container metrics."""
        try:
            containers = self.docker_client.containers.list(all=True)
            
            # Count containers by type
            container_counts = {'acp': 0, 'function': 0, 'persistent': 0, 'unknown': 0}
            running_counts = {'acp': 0, 'function': 0, 'persistent': 0, 'unknown': 0}
            stopped_counts = {'acp': 0, 'function': 0, 'persistent': 0, 'unknown': 0}
            
            for container in containers:
                # Try to determine container type from name
                container_type = 'unknown'
                if container.name.startswith('acp-'):
                    container_type = 'acp'
                elif container.name.startswith('func-'):
                    container_type = 'function'
                elif container.name.startswith('persis-'):
                    container_type = 'persistent'
                
                container_counts[container_type] += 1
                
                if container.status == 'running':
                    running_counts[container_type] += 1
                else:
                    stopped_counts[container_type] += 1
            
            # Update system metrics
            for container_type in ['acp', 'function', 'persistent', 'unknown']:
                self.total_containers.labels(deployment_type=container_type).set(container_counts[container_type])
                self.running_containers.labels(deployment_type=container_type).set(running_counts[container_type])
                self.stopped_containers.labels(deployment_type=container_type).set(stopped_counts[container_type])
                
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def record_execution_metrics(self, agent_id: str, deployment_type: str, duration: float, success: bool):
        """Record execution metrics for an agent."""
        try:
            if success:
                self.execution_success.labels(agent_id=agent_id, deployment_type=deployment_type).inc()
            else:
                self.execution_failure.labels(agent_id=agent_id, deployment_type=deployment_type).inc()
            
            self.execution_duration.labels(agent_id=agent_id, deployment_type=deployment_type).observe(duration)
            
        except Exception as e:
            logger.error(f"Error recording execution metrics: {e}")
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        try:
            return generate_latest(self.registry)
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return ""
    
    def get_container_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current container metrics."""
        try:
            summary = {
                'total_containers': len(self.container_metrics),
                'running_containers': sum(1 for m in self.container_metrics.values() if m['status'] == 'running'),
                'stopped_containers': sum(1 for m in self.container_metrics.values() if m['status'] != 'running'),
                'containers_by_type': {},
                'resource_usage': {
                    'total_cpu_percent': 0.0,
                    'total_memory_bytes': 0,
                    'total_memory_limit_bytes': 0
                }
            }
            
            # Group by deployment type
            for container_name, metrics in self.container_metrics.items():
                container_type = 'unknown'
                if container_name.startswith('acp-'):
                    container_type = 'acp'
                elif container_name.startswith('func-'):
                    container_type = 'function'
                elif container_name.startswith('persis-'):
                    container_type = 'persistent'
                
                if container_type not in summary['containers_by_type']:
                    summary['containers_by_type'][container_type] = {
                        'count': 0,
                        'running': 0,
                        'stopped': 0
                    }
                
                summary['containers_by_type'][container_type]['count'] += 1
                if metrics['status'] == 'running':
                    summary['containers_by_type'][container_type]['running'] += 1
                else:
                    summary['containers_by_type'][container_type]['stopped'] += 1
                
                # Aggregate resource usage
                if metrics['status'] == 'running':
                    summary['resource_usage']['total_cpu_percent'] += metrics['cpu_usage']
                    summary['resource_usage']['total_memory_bytes'] += metrics['memory_usage']
                    summary['resource_usage']['total_memory_limit_bytes'] += metrics['memory_limit']
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating metrics summary: {e}")
            return {}
    
    def cleanup_old_metrics(self, max_age_hours: int = 24):
        """Clean up old container metrics."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            containers_to_remove = []
            
            for container_name, metrics in self.container_metrics.items():
                if metrics['last_updated'] < cutoff_time:
                    containers_to_remove.append(container_name)
            
            for container_name in containers_to_remove:
                del self.container_metrics[container_name]
                logger.info(f"Cleaned up old metrics for container: {container_name}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")


# Global instance
metrics_service = PrometheusMetricsService()
