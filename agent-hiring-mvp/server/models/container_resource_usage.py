"""
Database models for container resource usage tracking and billing.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from .base import Base


class ContainerResourceUsage(Base):
    """Tracks container resource usage for billing purposes"""
    __tablename__ = "container_resource_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Container identification
    container_id = Column(String(255), nullable=False, index=True)
    container_name = Column(String(255), nullable=False, index=True)
    deployment_id = Column(String(50), ForeignKey("agent_deployments.deployment_id"), nullable=False)
    agent_id = Column(String(20), ForeignKey("agents.id"), nullable=False)
    hiring_id = Column(Integer, ForeignKey("hirings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Resource metrics (snapshot)
    cpu_usage_percent = Column(Float, nullable=False)  # CPU usage percentage
    memory_usage_bytes = Column(BigInteger, nullable=False)  # Memory usage in bytes
    memory_limit_bytes = Column(BigInteger, nullable=False)  # Memory limit in bytes
    network_rx_bytes = Column(BigInteger, nullable=False)  # Network received bytes
    network_tx_bytes = Column(BigInteger, nullable=False)  # Network transmitted bytes
    block_read_bytes = Column(BigInteger, nullable=False)  # Block read bytes
    block_write_bytes = Column(BigInteger, nullable=False)  # Block write bytes
    
    # Container status
    container_status = Column(String(20), nullable=False)  # running, stopped, etc.
    is_healthy = Column(Boolean, default=True)
    
    # Cost calculation
    cpu_cost_per_hour = Column(Float, nullable=False, default=0.0)  # Cost per CPU hour
    memory_cost_per_gb_hour = Column(Float, nullable=False, default=0.0)  # Cost per GB-hour
    network_cost_per_gb = Column(Float, nullable=False, default=0.0)  # Cost per GB transferred
    storage_cost_per_gb_hour = Column(Float, nullable=False, default=0.0)  # Cost per GB-hour stored
    
    # Calculated costs
    cpu_cost = Column(Float, nullable=False, default=0.0)  # CPU cost for this snapshot
    memory_cost = Column(Float, nullable=False, default=0.0)  # Memory cost for this snapshot
    network_cost = Column(Float, nullable=False, default=0.0)  # Network cost for this snapshot
    storage_cost = Column(Float, nullable=False, default=0.0)  # Storage cost for this snapshot
    total_cost = Column(Float, nullable=False, default=0.0)  # Total cost for this snapshot
    
    # Time tracking
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    collection_interval_seconds = Column(Integer, nullable=False, default=30)  # How often metrics are collected
    
    # Metadata
    deployment_type = Column(String(20), nullable=False)  # acp, function, persistent
    agent_type = Column(String(20), nullable=True)  # Type of agent
    resource_limits = Column(JSON, nullable=True)  # Applied resource limits
    
    # Relationships - only keep deployment for direct access
    deployment = relationship("AgentDeployment", back_populates="resource_usage")

    def __repr__(self) -> str:
        return f"<ContainerResourceUsage(id={self.id}, container='{self.container_name}', cost=${self.total_cost:.6f})>"


class AgentActivityLog(Base):
    """Tracks agent activity for billing and monitoring"""
    __tablename__ = "agent_activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Activity identification
    agent_id = Column(String(20), ForeignKey("agents.id"), nullable=False, index=True)
    hiring_id = Column(Integer, ForeignKey("hirings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deployment_id = Column(String(50), ForeignKey("agent_deployments.deployment_id"), nullable=False)
    
    # Activity details
    activity_type = Column(String(50), nullable=False)  # request, response, error, health_check
    activity_timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Request/Response data
    request_id = Column(String(64), nullable=True, index=True)  # Unique request identifier
    input_tokens = Column(Integer, nullable=True)  # Input token count
    output_tokens = Column(Integer, nullable=True)  # Output token count
    total_tokens = Column(Integer, nullable=True)  # Total token count
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    success = Column(Boolean, nullable=False, default=True)  # Whether the activity was successful
    error_message = Column(Text, nullable=True)  # Error message if failed
    
    # Resource usage at time of activity
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_bytes = Column(BigInteger, nullable=True)
    
    # Cost calculation
    token_cost = Column(Float, nullable=False, default=0.0)  # Cost for token usage
    compute_cost = Column(Float, nullable=False, default=0.0)  # Cost for compute resources
    total_cost = Column(Float, nullable=False, default=0.0)  # Total cost for this activity
    
    # Metadata
    deployment_type = Column(String(20), nullable=False)
    agent_type = Column(String(20), nullable=True)
    user_agent = Column(String(255), nullable=True)  # Client user agent
    ip_address = Column(String(45), nullable=True)  # Client IP address

    def __repr__(self) -> str:
        return f"<AgentActivityLog(id={self.id}, agent='{self.agent_id}', activity='{self.activity_type}', cost=${self.total_cost:.6f})>"


class ResourcePricing(Base):
    """Configuration for resource pricing"""
    __tablename__ = "resource_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Resource type
    resource_type = Column(String(50), nullable=False, unique=True)  # cpu, memory, network, storage

    # Pricing configuration
    base_price = Column(Float, nullable=False)  # Base price per unit
    price_unit = Column(String(20), nullable=False)  # per_hour, per_gb, per_request, etc.
    currency = Column(String(3), nullable=False, default="USD")
    
    # Tiered pricing
    pricing_tiers = Column(JSON, nullable=True)  # Tiered pricing structure
    volume_discounts = Column(JSON, nullable=True)  # Volume-based discounts
    
    # Time-based pricing
    peak_hour_multiplier = Column(Float, nullable=False, default=1.0)  # Multiplier for peak hours
    off_peak_multiplier = Column(Float, nullable=False, default=0.8)  # Multiplier for off-peak hours
    
    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)  # NULL means no expiration
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<ResourcePricing(id={self.id}, resource='{self.resource_type}', price=${self.base_price:.6f}/{self.price_unit})>"


class UsageAggregation(Base):
    """Aggregated usage data for billing and reporting"""
    __tablename__ = "usage_aggregations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Aggregation period
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(String(20), ForeignKey("agents.id"), nullable=False, index=True)
    hiring_id = Column(Integer, ForeignKey("hirings.id"), nullable=False, index=True)
    
    # Time period
    aggregation_period = Column(String(20), nullable=False)  # hourly, daily, monthly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Resource usage totals
    total_cpu_hours = Column(Float, nullable=False, default=0.0)
    total_memory_gb_hours = Column(Float, nullable=False, default=0.0)
    total_network_gb = Column(Float, nullable=False, default=0.0)
    total_storage_gb_hours = Column(Float, nullable=False, default=0.0)
    
    # Activity totals
    total_requests = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_response_time_ms = Column(Integer, nullable=False, default=0)
    
    # Cost totals
    total_cpu_cost = Column(Float, nullable=False, default=0.0)
    total_memory_cost = Column(Float, nullable=False, default=0.0)
    total_network_cost = Column(Float, nullable=False, default=0.0)
    total_storage_cost = Column(Float, nullable=False, default=0.0)
    total_token_cost = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    
    # Performance metrics
    average_response_time_ms = Column(Float, nullable=False, default=0.0)
    success_rate = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    deployment_type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<UsageAggregation(id={self.id}, user={self.user_id}, agent={self.agent_id}, cost=${self.total_cost:.6f})>"
