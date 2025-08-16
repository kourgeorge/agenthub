"""
Resource usage tracker service for monitoring agent containers and calculating costs.
Implements hourly billing model similar to AWS EC2.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
import docker
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models.container_resource_usage import ContainerResourceUsage, ResourcePricing, UsageAggregation, AgentActivityLog
from ..models.deployment import AgentDeployment
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..models.user import User
from ..models.execution import Execution
from ..models.resource_usage import ExecutionResourceUsage

logger = logging.getLogger(__name__)


class ResourceUsageTracker:
    """Tracks container resource usage and calculates costs for billing."""
    
    # Default AWS-competitive pricing (per hour) - independent of agent type
    # TESTING: Increased rates by 100x for visibility
    DEFAULT_PRICING = {
        "cpu": 4.16,          # $4.16 per vCPU-hour (100x for testing)
        "memory": 0.56,       # $0.56 per GB-hour (100x for testing)
        "network": 9.00,      # $9.00 per GB (100x for testing)
        "storage": 10.00      # $10.00 per GB-month (100x for testing)
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.docker_client = docker.from_env()
        
        # Initialize pricing from database or use defaults
        self.pricing = self._load_pricing_config()
        
        # Collection interval (30 seconds for accurate hourly billing)
        self.collection_interval = 30
        
    def _load_pricing_config(self) -> Dict[str, float]:
        """Load pricing configuration from database or use defaults."""
        try:
            # Try to load from database first
            pricing_records = self.db.query(ResourcePricing).filter(
                ResourcePricing.is_active == True
            ).all()
            
            if pricing_records:
                pricing = {}
                for record in pricing_records:
                    # Use the first active price for each resource type (agent-type independent)
                    if record.resource_type not in pricing:
                        pricing[record.resource_type] = record.base_price
                return pricing
        except Exception as e:
            logger.warning(f"Failed to load pricing from database: {e}")
        
        # Fall back to defaults
        return self.DEFAULT_PRICING
    
    def collect_container_metrics(self, deployment_id: str) -> Optional[ContainerResourceUsage]:
        """Collect current metrics for a specific container deployment."""
        try:
            # Get deployment info
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment or not deployment.container_name:
                return None
            
            # Get container stats from Docker
            try:
                container = self.docker_client.containers.get(deployment.container_name)
                stats = container.stats(stream=False)
                
                # Validate that we have the required stats structure
                if not stats or 'cpu_stats' not in stats or 'precpu_stats' not in stats:
                    logger.warning(f"Container {deployment.container_name} returned incomplete stats")
                    return None
                
                # Enhanced debug logging for stats structure
                logger.debug(f"Container {deployment.container_name} stats keys: {list(stats.keys())}")
                if 'cpu_stats' in stats:
                    logger.debug(f"CPU stats keys: {list(stats['cpu_stats'].keys())}")
                    if 'cpu_usage' in stats['cpu_stats']:
                        logger.debug(f"CPU usage keys: {list(stats['cpu_stats']['cpu_usage'].keys())}")
                    if 'system_cpu_usage' in stats['cpu_stats']:
                        logger.debug(f"System CPU usage available: {stats['cpu_stats']['system_cpu_usage']}")
                    else:
                        logger.debug(f"System CPU usage NOT available for {deployment.container_name}")
                if 'precpu_stats' in stats:
                    logger.debug(f"PreCPU stats keys: {list(stats['precpu_stats'].keys())}")
                    if 'cpu_usage' in stats['precpu_stats']:
                        logger.debug(f"PreCPU usage keys: {list(stats['precpu_stats']['cpu_usage'].keys())}")
                    if 'system_cpu_usage' in stats['precpu_stats']:
                        logger.debug(f"PreCPU system CPU usage available: {stats['precpu_stats']['system_cpu_usage']}")
                    else:
                        logger.debug(f"PreCPU system CPU usage NOT available for {deployment.container_name}")
                
            except docker.errors.NotFound:
                logger.warning(f"Container {deployment.container_name} not found")
                return None
            except Exception as e:
                logger.error(f"Error getting stats for container {deployment.container_name}: {e}")
                return None
            
            # Calculate CPU usage percentage
            # NOTE: The 'system_cpu_usage' field is not always available in Docker container stats,
            # especially on macOS or with certain container runtimes. This implementation provides
            # a fallback calculation method to handle missing fields gracefully.
            try:
                # Check if we have the required CPU stats fields
                if ('cpu_stats' in stats and 'precpu_stats' in stats and 
                    'cpu_usage' in stats['cpu_stats'] and 'cpu_usage' in stats['precpu_stats']):
                    
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                    
                    # Try to get system CPU usage - this field might not exist on all platforms
                    system_delta = 0
                    if ('system_cpu_usage' in stats['cpu_stats'] and 
                        'system_cpu_usage' in stats['precpu_stats']):
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                    else:
                        # Fallback: use online_cpus if available, or estimate from other sources
                        try:
                            # Try to get CPU count from various sources
                            cpu_count = 1
                            if 'online_cpus' in stats['cpu_stats']:
                                cpu_count = stats['cpu_stats']['online_cpus']
                            elif 'cpu_usage' in stats['cpu_stats'] and 'percpu_usage' in stats['cpu_stats']['cpu_usage']:
                                cpu_count = len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
                            
                            # If we can't get system CPU usage, estimate CPU usage from container CPU delta
                            # This is a fallback method that's less accurate but more reliable
                            if cpu_delta > 0:
                                # Estimate CPU usage based on container CPU time delta
                                # This assumes the container is using a reasonable amount of CPU
                                # and provides a conservative estimate
                                cpu_usage_percent = min(cpu_delta / 1000000.0, 100.0)  # Conservative estimate
                            else:
                                cpu_usage_percent = 0.0
                            
                            logger.debug(f"Using fallback CPU calculation for {deployment.container_name}: "
                                       f"cpu_delta={cpu_delta}, estimated_usage={cpu_usage_percent:.2f}%")
                            
                        except (KeyError, TypeError) as e:
                            logger.debug(f"Fallback CPU calculation failed for {deployment.container_name}: {e}")
                            cpu_usage_percent = 0.0
                    
                    # If we have system_delta, use the standard calculation
                    if system_delta > 0:
                        # Get CPU count - handle cases where percpu_usage might not exist
                        try:
                            cpu_count = len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
                        except (KeyError, TypeError):
                            # Fallback: try to get CPU count from other sources
                            try:
                                cpu_count = stats['cpu_stats'].get('online_cpus', 1)
                            except (KeyError, TypeError):
                                cpu_count = 1  # Default to 1 CPU if we can't determine
                        
                        cpu_usage_percent = (cpu_delta / system_delta) * cpu_count * 100.0
                    elif system_delta == 0 and 'cpu_usage_percent' not in locals():
                        # Container is idle or stats are not yet available
                        cpu_usage_percent = 0.0
                        
                else:
                    logger.debug(f"Missing required CPU stats fields for {deployment.container_name}")
                    cpu_usage_percent = 0.0
                    
            except (KeyError, TypeError) as e:
                logger.warning(f"Error calculating CPU usage for {deployment.container_name}: {e}")
                cpu_usage_percent = 0.0
            except Exception as e:
                logger.error(f"Unexpected error calculating CPU usage for {deployment.container_name}: {e}")
                cpu_usage_percent = 0.0
            
            # Memory usage
            try:
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 0)
                
                # Ensure we have valid memory values
                if memory_usage is None or memory_limit is None:
                    logger.warning(f"Container {deployment.container_name} has invalid memory stats")
                    memory_usage = 0
                    memory_limit = 0
                    
            except (KeyError, TypeError) as e:
                logger.warning(f"Error getting memory stats for {deployment.container_name}: {e}")
                memory_usage = 0
                memory_limit = 0
            
            # Network stats
            try:
                network_stats = stats.get('networks', {})
                rx_bytes = sum(net.get('rx_bytes', 0) for net in network_stats.values()) if network_stats else 0
                tx_bytes = sum(net.get('tx_bytes', 0) for net in network_stats.values()) if network_stats else 0
            except (KeyError, TypeError) as e:
                logger.warning(f"Error getting network stats for {deployment.container_name}: {e}")
                rx_bytes = 0
                tx_bytes = 0
            
            # Block I/O stats
            try:
                block_stats = stats.get('blkio_stats', {}).get('io_service_bytes', [])
                read_bytes = sum(stat.get('value', 0) for stat in block_stats if stat.get('op') == 'Read')
                write_bytes = sum(stat.get('value', 0) for stat in block_stats if stat.get('op') == 'Write')
            except (KeyError, TypeError) as e:
                logger.warning(f"Error getting block I/O stats for {deployment.container_name}: {e}")
                read_bytes = 0
                write_bytes = 0
            
            # Get pricing for this resource type (agent-type independent)
            deployment_type = deployment.deployment_type or "function"
            cpu_cost_per_hour = self.pricing.get("cpu", 4.16)
            memory_cost_per_gb_hour = self.pricing.get("memory", 0.56)
            network_cost_per_gb = self.pricing.get("network", 9.00)
            storage_cost_per_gb_hour = self.pricing.get("storage", 10.00) / 730  # Convert monthly to hourly
            
            # Calculate costs for this snapshot (30-second interval)
            interval_hours = self.collection_interval / 3600.0
            
            # CPU cost: proportional to usage percentage
            cpu_cost = (cpu_usage_percent / 100.0) * cpu_cost_per_hour * interval_hours
            
            # Memory cost: based on actual usage
            memory_gb = memory_usage / (1024**3)
            memory_cost = memory_gb * memory_cost_per_gb_hour * interval_hours
            
            # Network cost: based on data transfer
            network_gb = (rx_bytes + tx_bytes) / (1024**3)
            network_cost = network_gb * network_cost_per_gb
            
            # Storage cost: based on memory limit (storage allocation)
            storage_gb = memory_limit / (1024**3)
            storage_cost = storage_gb * storage_cost_per_gb_hour * interval_hours
            
            # Total cost for this snapshot
            total_cost = cpu_cost + memory_cost + network_cost + storage_cost
            
            # Debug logging for cost breakdown
            logger.debug(f"Cost breakdown for {deployment.container_name}: "
                        f"CPU=${cpu_cost:.6f}, Memory=${memory_cost:.6f}, "
                        f"Network=${network_cost:.6f}, Storage=${storage_cost:.6f}, "
                        f"Total=${total_cost:.6f}")
            
            # Create resource usage record
            resource_usage = ContainerResourceUsage(
                container_id=container.id,
                container_name=deployment.container_name,
                deployment_id=deployment_id,
                agent_id=deployment.agent_id,
                hiring_id=deployment.hiring_id,
                user_id=deployment.hiring.user_id,
                
                # Resource metrics
                cpu_usage_percent=cpu_usage_percent,
                memory_usage_bytes=memory_usage,
                memory_limit_bytes=memory_limit,
                network_rx_bytes=rx_bytes,
                network_tx_bytes=tx_bytes,
                block_read_bytes=read_bytes,
                block_write_bytes=write_bytes,
                
                # Container status
                container_status=getattr(container, 'status', 'unknown'),
                is_healthy=getattr(deployment, 'is_healthy', False),
                
                # Pricing configuration
                cpu_cost_per_hour=cpu_cost_per_hour,
                memory_cost_per_gb_hour=memory_cost_per_gb_hour,
                network_cost_per_gb=network_cost_per_gb,
                storage_cost_per_gb_hour=storage_cost_per_gb_hour,
                
                # Calculated costs
                cpu_cost=cpu_cost,
                memory_cost=memory_cost,
                network_cost=network_cost,
                storage_cost=storage_cost,
                total_cost=total_cost,
                
                # Time tracking
                snapshot_timestamp=datetime.now(timezone.utc),
                collection_interval_seconds=self.collection_interval,
                
                # Metadata
                deployment_type=deployment_type,
                agent_type=getattr(deployment.agent, 'agent_type', None) if deployment.agent else None,
                resource_limits=deployment.deployment_config.get("resources") if deployment.deployment_config else None
            )
            
            # Save to database
            self.db.add(resource_usage)
            self.db.commit()
            
            # Calculate memory in GB for logging
            memory_gb = memory_usage / (1024**3) if memory_usage else 0
            
            logger.debug(f"Collected metrics for {deployment.container_name}: CPU={cpu_usage_percent:.1f}%, "
                        f"Memory={memory_gb:.2f}GB, Cost=${total_cost:.6f}")
            
            return resource_usage
            
        except Exception as e:
            logger.error(f"Error collecting metrics for deployment {deployment_id}: {e}")
            self.db.rollback()
            return None
    
    def calculate_hourly_usage(self, deployment_id: str, hour_start: datetime) -> Dict[str, Any]:
        """Calculate hourly usage and costs for a specific deployment."""
        try:
            hour_end = hour_start + timedelta(hours=1)
            
            # Get all snapshots for this hour
            snapshots = self.db.query(ContainerResourceUsage).filter(
                and_(
                    ContainerResourceUsage.deployment_id == deployment_id,
                    ContainerResourceUsage.snapshot_timestamp >= hour_start,
                    ContainerResourceUsage.snapshot_timestamp < hour_end
                )
            ).order_by(ContainerResourceUsage.snapshot_timestamp).all()
            
            if not snapshots:
                return {
                    "deployment_id": deployment_id,
                    "hour_start": hour_start,
                    "hour_end": hour_end,
                    "snapshots_count": 0,
                    "total_cost": 0.0,
                    "average_cpu_percent": 0.0,
                    "average_memory_gb": 0.0,
                    "total_network_gb": 0.0,
                    "status": "no_data"
                }
            
            # Calculate averages and totals
            total_cost = sum(s.total_cost for s in snapshots)
            average_cpu = sum(s.cpu_usage_percent for s in snapshots) / len(snapshots)
            average_memory = sum(s.memory_usage_bytes for s in snapshots) / len(snapshots) / (1024**3)
            
            # Network usage (cumulative)
            total_network_rx = sum(s.network_rx_bytes for s in snapshots)
            total_network_tx = sum(s.network_tx_bytes for s in snapshots)
            total_network_gb = (total_network_rx + total_network_tx) / (1024**3)
            
            # Determine if container was running the full hour
            running_snapshots = [s for s in snapshots if s.container_status == "running"]
            running_percentage = len(running_snapshots) / len(snapshots) if snapshots else 0
            
            return {
                "deployment_id": deployment_id,
                "hour_start": hour_start,
                "hour_end": hour_end,
                "snapshots_count": len(snapshots),
                "running_percentage": running_percentage,
                "total_cost": total_cost,
                "average_cpu_percent": average_cpu,
                "average_memory_gb": average_memory,
                "total_network_gb": total_network_gb,
                "status": "active" if running_percentage > 0.5 else "inactive"
            }
            
        except Exception as e:
            logger.error(f"Error calculating hourly usage for {deployment_id}: {e}")
            return {}
    
    def aggregate_daily_usage(self, user_id: int, date: datetime) -> Dict[str, Any]:
        """Aggregate daily usage for a user."""
        try:
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            # Get all deployments for this user on this date
            deployments = self.db.query(AgentDeployment).join(Hiring).filter(
                and_(
                    Hiring.user_id == user_id,
                    AgentDeployment.created_at >= date_start,
                    AgentDeployment.created_at < date_end
                )
            ).all()
            
            daily_summary = {
                "user_id": user_id,
                "date": date_start.date().isoformat(),
                "deployments": [],
                "total_cost": 0.0,
                "total_cpu_hours": 0.0,
                "total_memory_gb_hours": 0.0,
                "total_network_gb": 0.0,
                "total_requests": 0
            }
            
            for deployment in deployments:
                # Calculate hourly usage for this deployment
                deployment_costs = []
                deployment_cpu_hours = 0.0
                deployment_memory_gb_hours = 0.0
                deployment_network_gb = 0.0
                
                # Check each hour of the day
                for hour in range(24):
                    hour_start = date_start + timedelta(hours=hour)
                    hourly_usage = self.calculate_hourly_usage(deployment.deployment_id, hour_start)
                    
                    if hourly_usage.get("snapshots_count", 0) > 0:
                        deployment_costs.append(hourly_usage["total_cost"])
                        deployment_cpu_hours += hourly_usage["average_cpu_percent"] / 100.0  # Convert to CPU-hours
                        deployment_memory_gb_hours += hourly_usage["average_memory_gb"]
                        deployment_network_gb += hourly_usage["total_network_gb"]
                
                # Get activity count for this deployment
                activity_count = self.db.query(AgentActivityLog).filter(
                    AgentActivityLog.deployment_id == deployment.deployment_id,
                    AgentActivityLog.activity_timestamp >= date_start,
                    AgentActivityLog.activity_timestamp < date_end
                ).count()
                
                deployment_summary = {
                    "deployment_id": deployment.deployment_id,
                    "agent_id": deployment.agent_id,
                    "deployment_type": deployment.deployment_type,
                    "total_cost": sum(deployment_costs),
                    "cpu_hours": deployment_cpu_hours,
                    "memory_gb_hours": deployment_memory_gb_hours,
                    "network_gb": deployment_network_gb,
                    "requests": activity_count,
                    "status": deployment.status
                }
                
                daily_summary["deployments"].append(deployment_summary)
                daily_summary["total_cost"] += deployment_summary["total_cost"]
                daily_summary["total_cpu_hours"] += deployment_summary["cpu_hours"]
                daily_summary["total_memory_gb_hours"] += deployment_summary["memory_gb_hours"]
                daily_summary["total_network_gb"] += deployment_summary["network_gb"]
                daily_summary["total_requests"] += deployment_summary["requests"]
            
            # Save daily aggregation
            self._save_daily_aggregation(user_id, date_start, daily_summary)
            
            return daily_summary
            
        except Exception as e:
            logger.error(f"Error aggregating daily usage for user {user_id}: {e}")
            return {}
    
    def _save_daily_aggregation(self, user_id: int, date: datetime, summary: Dict[str, Any]):
        """Save daily usage aggregation to database."""
        try:
            # Check if aggregation already exists
            existing = self.db.query(UsageAggregation).filter(
                and_(
                    UsageAggregation.user_id == user_id,
                    UsageAggregation.aggregation_period == "daily",
                    UsageAggregation.period_start == date
                )
            ).first()
            
            if existing:
                # Update existing
                existing.total_cpu_hours = summary["total_cpu_hours"]
                existing.total_memory_gb_hours = summary["total_memory_gb_hours"]
                existing.total_network_gb = summary["total_network_gb"]
                existing.total_requests = summary["total_requests"]
                existing.total_cost = summary["total_cost"]
            else:
                # Create new aggregation
                aggregation = UsageAggregation(
                    user_id=user_id,
                    agent_id="",  # Will be updated with specific agent data
                    hiring_id=0,   # Will be updated with specific hiring data
                    aggregation_period="daily",
                    period_start=date,
                    period_end=date + timedelta(days=1),
                    total_cpu_hours=summary["total_cpu_hours"],
                    total_memory_gb_hours=summary["total_memory_gb_hours"],
                    total_network_gb=summary["total_network_gb"],
                    total_requests=summary["total_requests"],
                    total_cost=summary["total_cost"],
                    deployment_type="mixed"  # Will be updated with specific type
                )
                self.db.add(aggregation)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error saving daily aggregation: {e}")
            self.db.rollback()
    
    def create_hiring_aggregation(self, hiring_id: int) -> Dict[str, Any]:
        """Create hiring-level resource usage aggregation for billing."""
        try:
            # Get hiring details
            hiring = self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
            if not hiring:
                logger.error(f"Hiring {hiring_id} not found")
                return {}
            
            # Get all container usage for this hiring
            container_usage = self.db.query(ContainerResourceUsage).filter(
                ContainerResourceUsage.hiring_id == hiring_id
            ).all()
            
            if not container_usage:
                logger.info(f"No container usage found for hiring {hiring_id}")
                return {}
            
            # Calculate totals
            total_cpu_hours = 0.0
            total_memory_gb_hours = 0.0
            total_network_gb = 0.0
            total_storage_gb_hours = 0.0
            total_cost = 0.0
            total_snapshots = len(container_usage)
            
            for usage in container_usage:
                # Convert snapshot costs to hourly rates
                interval_hours = usage.collection_interval_seconds / 3600.0
                
                # CPU: convert percentage to hours
                cpu_hours = (usage.cpu_usage_percent / 100.0) * interval_hours
                total_cpu_hours += cpu_hours
                
                # Memory: convert bytes to GB-hours
                memory_gb = usage.memory_usage_bytes / (1024**3)
                memory_hours = memory_gb * interval_hours
                total_memory_gb_hours += memory_hours
                
                # Network: convert bytes to GB
                network_gb = (usage.network_rx_bytes + usage.network_tx_bytes) / (1024**3)
                total_network_gb += network_gb
                
                # Storage: based on memory limit
                storage_gb = usage.memory_limit_bytes / (1024**3)
                storage_hours = storage_gb * interval_hours
                total_storage_gb_hours += storage_hours
                
                # Total cost
                total_cost += usage.total_cost
            
            # Create or update hiring aggregation
            existing = self.db.query(UsageAggregation).filter(
                and_(
                    UsageAggregation.hiring_id == hiring_id,
                    UsageAggregation.aggregation_period == "hiring"
                )
            ).first()
            
            if existing:
                # Update existing
                existing.total_cpu_hours = total_cpu_hours
                existing.total_memory_gb_hours = total_memory_gb_hours
                existing.total_network_gb = total_network_gb
                existing.total_storage_gb_hours = total_storage_gb_hours
                existing.total_cost = total_cost
                existing.period_end = datetime.now(timezone.utc)
            else:
                # Create new hiring aggregation
                aggregation = UsageAggregation(
                    user_id=hiring.user_id,
                    agent_id=hiring.agent_id,
                    hiring_id=hiring_id,
                    aggregation_period="hiring",
                    period_start=hiring.hired_at,
                    period_end=datetime.now(timezone.utc),
                    total_cpu_hours=total_cpu_hours,
                    total_memory_gb_hours=total_memory_gb_hours,
                    total_network_gb=total_network_gb,
                    total_storage_gb_hours=total_storage_gb_hours,
                    total_cost=total_cost,
                    total_requests=total_snapshots,
                    deployment_type="acp"  # Default, will be updated
                )
                self.db.add(aggregation)
            
            self.db.commit()
            
            hiring_summary = {
                "hiring_id": hiring_id,
                "agent_id": hiring.agent_id,
                "user_id": hiring.user_id,
                "total_cpu_hours": total_cpu_hours,
                "total_memory_gb_hours": total_memory_gb_hours,
                "total_network_gb": total_network_gb,
                "total_storage_gb_hours": total_storage_gb_hours,
                "total_cost": total_cost,
                "total_snapshots": total_snapshots,
                "hiring_start": hiring.hired_at,
                "hiring_end": datetime.now(timezone.utc)
            }
            
            logger.info(f"Created hiring aggregation for hiring {hiring_id}: ${total_cost:.6f}")
            return hiring_summary
            
        except Exception as e:
            logger.error(f"Error creating hiring aggregation for hiring {hiring_id}: {e}")
            self.db.rollback()
            return {}
    
    def get_user_monthly_billing(self, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Get monthly billing summary for a user."""
        try:
            month_start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            
            # Get daily aggregations for the month
            daily_aggregations = self.db.query(UsageAggregation).filter(
                and_(
                    UsageAggregation.user_id == user_id,
                    UsageAggregation.aggregation_period == "daily",
                    UsageAggregation.period_start >= month_start,
                    UsageAggregation.period_start < month_end
                )
            ).all()
            
            monthly_summary = {
                "user_id": user_id,
                "year": year,
                "month": month,
                "total_cost": 0.0,
                "total_cpu_hours": 0.0,
                "total_memory_gb_hours": 0.0,
                "total_network_gb": 0.0,
                "total_requests": 0,
                "daily_breakdown": [],
                "deployment_breakdown": {}
            }
            
            for daily in daily_aggregations:
                monthly_summary["total_cost"] += daily.total_cost
                monthly_summary["total_cpu_hours"] += daily.total_cpu_hours
                monthly_summary["total_memory_gb_hours"] += daily.total_memory_gb_hours
                monthly_summary["total_network_gb"] += daily.total_network_gb
                monthly_summary["total_requests"] += daily.total_requests
                
                monthly_summary["daily_breakdown"].append({
                    "date": daily.period_start.date().isoformat(),
                    "cost": daily.total_cost,
                    "cpu_hours": daily.total_cpu_hours,
                    "memory_gb_hours": daily.total_memory_gb_hours,
                    "requests": daily.total_requests
                })
            
            # Get deployment breakdown
            deployments = self.db.query(AgentDeployment).join(Hiring).filter(
                and_(
                    Hiring.user_id == user_id,
                    AgentDeployment.created_at >= month_start,
                    AgentDeployment.created_at < month_end
                )
            ).all()
            
            for deployment in deployments:
                deployment_type = deployment.deployment_type or "unknown"
                if deployment_type not in monthly_summary["deployment_breakdown"]:
                    monthly_summary["deployment_breakdown"][deployment_type] = {
                        "count": 0,
                        "total_cost": 0.0,
                        "total_hours": 0.0
                    }
                
                monthly_summary["deployment_breakdown"][deployment_type]["count"] += 1
                
                # Calculate deployment costs for the month
                deployment_costs = self.db.query(func.sum(ContainerResourceUsage.total_cost)).filter(
                    ContainerResourceUsage.deployment_id == deployment.deployment_id,
                    ContainerResourceUsage.snapshot_timestamp >= month_start,
                    ContainerResourceUsage.snapshot_timestamp < month_end
                ).scalar() or 0.0
                
                monthly_summary["deployment_breakdown"][deployment_type]["total_cost"] += deployment_costs
                
                # Calculate total running hours
                running_hours = self.db.query(func.count(ContainerResourceUsage.id)).filter(
                    and_(
                        ContainerResourceUsage.deployment_id == deployment.deployment_id,
                        ContainerResourceUsage.snapshot_timestamp >= month_start,
                        ContainerResourceUsage.snapshot_timestamp < month_end,
                        ContainerResourceUsage.container_status == "running"
                    )
                ).scalar() or 0
                
                monthly_summary["deployment_breakdown"][deployment_type]["total_hours"] += running_hours * (self.collection_interval / 3600.0)
            
            return monthly_summary
            
        except Exception as e:
            logger.error(f"Error getting monthly billing for user {user_id}: {e}")
            return {}
    
    def estimate_deployment_cost(self, deployment_type: str, duration_hours: float, 
                               avg_cpu_percent: float = 50.0, avg_memory_gb: float = 1.0) -> Dict[str, float]:
        """Estimate cost for a deployment before it starts."""
        try:
            cpu_cost_per_hour = self.pricing.get("cpu", 4.16)
            memory_cost_per_gb_hour = self.pricing.get("memory", 0.56)
            storage_cost_per_gb_hour = self.pricing.get("storage", 10.00) / 730
            
            # Calculate estimated costs
            cpu_cost = (avg_cpu_percent / 100.0) * cpu_cost_per_hour * duration_hours
            memory_cost = avg_memory_gb * memory_cost_per_gb_hour * duration_hours
            storage_cost = avg_memory_gb * storage_cost_per_gb_hour * duration_hours
            
            total_cost = cpu_cost + memory_cost + storage_cost
            
            return {
                "cpu_cost": cpu_cost,
                "memory_cost": memory_cost,
                "storage_cost": storage_cost,
                "total_cost": total_cost,
                "cost_per_hour": total_cost / duration_hours if duration_hours > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error estimating deployment cost: {e}")
            return {"total_cost": 0.0, "cost_per_hour": 0.0}
    
    def get_hiring_billing(self, hiring_id: int) -> Dict[str, Any]:
        """Get billing information for a specific hiring."""
        try:
            # First create/update the hiring aggregation
            hiring_summary = self.create_hiring_aggregation(hiring_id)
            if not hiring_summary:
                return {}
            
            # Get the hiring details
            hiring = self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
            if not hiring:
                return {}
            
            # Get all executions for this hiring
            executions = self.db.query(Execution).filter(Execution.hiring_id == hiring_id).all()
            
            # Get execution resource usage from resource_usage.py
            execution_costs = self.db.query(func.sum(ExecutionResourceUsage.cost)).filter(
                ExecutionResourceUsage.execution_id.in_([e.id for e in executions])
            ).scalar() or 0.0
            
            # Calculate total cost (container + execution)
            total_cost = hiring_summary["total_cost"] + execution_costs
            
            billing_info = {
                "hiring_id": hiring_id,
                "agent_id": hiring.agent_id,
                "user_id": hiring.user_id,
                "hiring_start": hiring.hired_at,
                "hiring_end": datetime.now(timezone.utc),
                "billing_cycle": hiring.billing_cycle or "monthly",
                
                # Container resource costs
                "container_cpu_hours": hiring_summary["total_cpu_hours"],
                "container_memory_gb_hours": hiring_summary["total_memory_gb_hours"],
                "container_network_gb": hiring_summary["total_network_gb"],
                "container_storage_gb_hours": hiring_summary["total_storage_gb_hours"],
                "container_cost": hiring_summary["total_cost"],
                
                # Execution resource costs
                "execution_cost": execution_costs,
                "total_executions": len(executions),
                
                # Total billing
                "total_cost": total_cost,
                
                # Cost breakdown
                "cost_breakdown": {
                    "container_resources": hiring_summary["total_cost"],
                    "execution_resources": execution_costs,
                    "total": total_cost
                }
            }
            
            return billing_info
            
        except Exception as e:
            logger.error(f"Error getting hiring billing for hiring {hiring_id}: {e}")
            return {}
