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

from ..models.container_resource_usage import ContainerResourceUsage, ResourcePricing, UsageAggregation
from ..models.agent_activity_log import AgentActivityLog
from ..models.deployment import AgentDeployment
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..models.user import User

logger = logging.getLogger(__name__)


class ResourceUsageTracker:
    """Tracks container resource usage and calculates costs for billing."""
    
    # Default AWS-competitive pricing (per hour)
    DEFAULT_PRICING = {
        "cpu": {
            "acp": 0.0416,        # $0.0416 per vCPU-hour (t3.micro equivalent)
            "function": 0.0208,   # $0.0208 per vCPU-hour (t3.nano equivalent)
            "persistent": 0.0312  # $0.0312 per vCPU-hour (t3.small equivalent)
        },
        "memory": {
            "acp": 0.0056,        # $0.0056 per GB-hour
            "function": 0.0028,   # $0.0028 per GB-hour
            "persistent": 0.0042  # $0.0042 per GB-hour
        },
        "network": {
            "acp": 0.09,          # $0.09 per GB (outbound)
            "function": 0.09,     # $0.09 per GB (outbound)
            "persistent": 0.09    # $0.09 per GB (outbound)
        },
        "storage": {
            "acp": 0.10,          # $0.10 per GB-month (EBS gp3 equivalent)
            "function": 0.10,     # $0.10 per GB-month
            "persistent": 0.10    # $0.10 per GB-month
        }
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.docker_client = docker.from_env()
        
        # Initialize pricing from database or use defaults
        self.pricing = self._load_pricing_config()
        
        # Collection interval (30 seconds for accurate hourly billing)
        self.collection_interval = 30
        
    def _load_pricing_config(self) -> Dict[str, Dict[str, float]]:
        """Load pricing configuration from database or use defaults."""
        try:
            # Try to load from database first
            pricing_records = self.db.query(ResourcePricing).filter(
                ResourcePricing.is_active == True
            ).all()
            
            if pricing_records:
                pricing = {}
                for record in pricing_records:
                    if record.resource_type not in pricing:
                        pricing[record.resource_type] = {}
                    pricing[record.resource_type][record.deployment_type] = record.base_price
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
            except docker.errors.NotFound:
                logger.warning(f"Container {deployment.container_name} not found")
                return None
            
            # Calculate CPU usage percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0:
                cpu_usage_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            else:
                cpu_usage_percent = 0.0
            
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
            
            # Get pricing for this deployment type
            deployment_type = deployment.deployment_type or "function"
            cpu_cost_per_hour = self.pricing.get("cpu", {}).get(deployment_type, 0.02)
            memory_cost_per_gb_hour = self.pricing.get("memory", {}).get(deployment_type, 0.003)
            network_cost_per_gb = self.pricing.get("network", {}).get(deployment_type, 0.09)
            storage_cost_per_gb_hour = self.pricing.get("storage", {}).get(deployment_type, 0.10) / 730  # Convert monthly to hourly
            
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
                container_status=container.status,
                is_healthy=deployment.is_healthy,
                
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
                agent_type=deployment.agent.agent_type if deployment.agent else None,
                resource_limits=deployment.deployment_config.get("resources") if deployment.deployment_config else None
            )
            
            # Save to database
            self.db.add(resource_usage)
            self.db.commit()
            
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
            cpu_cost_per_hour = self.pricing.get("cpu", {}).get(deployment_type, 0.02)
            memory_cost_per_gb_hour = self.pricing.get("memory", {}).get(deployment_type, 0.003)
            storage_cost_per_gb_hour = self.pricing.get("storage", {}).get(deployment_type, 0.10) / 730
            
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
