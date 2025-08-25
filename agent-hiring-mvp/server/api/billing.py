"""Billing API endpoints for tracking costs and resource usage."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models.execution import Execution
from ..models.hiring import Hiring
from ..models.agent import Agent
from ..models.resource_usage import ExecutionResourceUsage
from ..models.container_resource_usage import ContainerResourceUsage
from ..models.deployment import AgentDeployment
from ..models.user import User
from ..config.payment_config import PaymentConfig
from ..services.payment_service import PaymentService
from ..services.invoice_service import InvoiceService
from ..services.enhanced_billing_service import EnhancedBillingService
from ..middleware.auth import get_current_user
from ..middleware.permissions import require_billing_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


class AddPaymentMethodRequest(BaseModel):
    """Request model for adding a payment method"""
    user_id: int
    payment_method: Dict[str, Any]
    
    class Config:
        # Allow extra fields to be ignored
        extra = "ignore"
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if v is None or v <= 0:
            raise ValueError('user_id must be a positive integer')
        return v


# Enhanced Billing Models
class CostEstimateRequest(BaseModel):
    """Request model for cost estimation"""
    deployment_type: str
    duration_hours: float
    avg_cpu_percent: float = 50.0
    avg_memory_gb: float = 1.0
    
    @validator('deployment_type')
    def validate_deployment_type(cls, v):
        if v not in ['acp', 'function', 'persistent']:
            raise ValueError('deployment_type must be one of: acp, function, persistent')
        return v
    
    @validator('duration_hours')
    def validate_duration_hours(cls, v):
        if v <= 0:
            raise ValueError('duration_hours must be positive')
        return v
    
    @validator('avg_cpu_percent')
    def validate_cpu_percent(cls, v):
        if v < 0 or v > 100:
            raise ValueError('avg_cpu_percent must be between 0 and 100')
        return v
    
    @validator('avg_memory_gb')
    def validate_memory_gb(cls, v):
        if v <= 0:
            raise ValueError('avg_memory_gb must be positive')
        return v




@router.get("/summary")
@require_billing_permission("view")
async def get_billing_summary(
    user_id: int = Query(..., description="User ID to get billing for"),
    months: int = Query(12, description="Number of months to fetch"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing summary for the last N months for a specific user."""
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=months * 30)
        
        # Initialize monthly data structure
        monthly_data = {}
        
        # Get executions for this specific user only
        executions = db.query(Execution).filter(
            and_(
                Execution.created_at >= start_date,
                Execution.created_at <= end_date,
                Execution.user_id == user_id  # Filter by user
            )
        ).all()
        
        for execution in executions:
            month_key = execution.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_charges": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "hirings": [],
                    "executions": []
                }
            
            # Get agent information for this execution
            agent_name = "Unknown Agent"
            agent_type = "unknown"
            agent_price_per_use = 0.0
            if execution.hiring_id:
                hiring = db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
                if hiring:
                    agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                    if agent:
                        agent_name = agent.name
                        agent_type = agent.agent_type
                        agent_price_per_use = agent.price_per_use or 0.0
            
            # Add execution data
            monthly_data[month_key]["total_executions"] += 1
            monthly_data[month_key]["executions"].append({
                "id": execution.id,
                "execution_id": execution.execution_id,  # Add the actual execution_id
                "hiring_id": execution.hiring_id,
                "agent_name": agent_name,  # Use the looked up agent name
                "agent_type": agent_type,  # Add agent type
                "agent_price_per_use": agent_price_per_use,  # Add agent pricing
                "executed_at": execution.created_at.isoformat(),
                "status": execution.status,
                "execution_time": execution.duration_ms / 1000 if execution.duration_ms else None,
                "charges": 0.0,  # Will be calculated from resource usage + agent pricing
                "resource_usage": []
            })
        
        # Get hiring data for this specific user only
        hirings = db.query(Hiring).filter(
            and_(
                Hiring.created_at >= start_date,
                Hiring.created_at <= end_date,
                Hiring.user_id == user_id  # Filter by user
            )
        ).all()
        
        for hiring in hirings:
            month_key = hiring.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_charges": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "hirings": [],
                    "executions": [],
                    "container_resources": {
                        "total_cpu_hours": 0.0,
                        "total_memory_gb_hours": 0.0,
                        "total_storage_gb": 0.0,
                        "total_cost": 0.0
                    }
                }
            
            # Get agent information
            agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            agent_name = agent.name if agent else "Unknown Agent"
            agent_type = agent.agent_type if agent else "unknown"
            
            # Count executions for this hiring
            execution_count = db.query(Execution).filter(
                Execution.hiring_id == hiring.id
            ).count()
            
            monthly_data[month_key]["total_hirings"] += 1
            monthly_data[month_key]["hirings"].append({
                "id": hiring.id,
                "agent_id": hiring.agent_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "status": hiring.status,
                "hired_at": hiring.created_at.isoformat(),
                "billing_cycle": "monthly",  # Default for now
                "total_executions": execution_count,
                "charges": 0.0  # Will be calculated from resource usage
            })
        
        # Get resource usage data for this user's executions and calculate charges
        if executions:
            execution_ids = [execution.id for execution in executions]
            resource_usage = db.query(ExecutionResourceUsage).filter(
                and_(
                    ExecutionResourceUsage.created_at >= start_date,
                    ExecutionResourceUsage.created_at <= end_date,
                    ExecutionResourceUsage.execution_id.in_(execution_ids)  # Filter by user's executions
                )
            ).all()
            
            # Calculate charges from resource usage
            for usage in resource_usage:
                # Find the execution this usage belongs to
                for month_data in monthly_data.values():
                    for execution in month_data["executions"]:
                        if str(execution["id"]) == str(usage.execution_id):
                            execution["charges"] += usage.cost
                            execution["resource_usage"].append({
                                "resource_type": usage.resource_type,
                                "provider": usage.resource_provider,
                                "model": usage.resource_model,
                                "operation_type": usage.operation_type,
                                "cost": usage.cost,
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                                "duration_ms": usage.duration_ms,
                                "created_at": usage.created_at.isoformat() if usage.created_at else None
                            })
                            break
        
            # Calculate charges from agent pricing (price_per_use)
            for month_data in monthly_data.values():
                for execution in month_data["executions"]:
                    if execution.get("agent_price_per_use", 0.0) > 0.0:
                        # Add agent per-use cost to execution charges
                        execution["charges"] += execution["agent_price_per_use"]
                        # Add agent pricing to resource usage for transparency
                        execution["resource_usage"].append({
                            "resource_type": "agent_execution",
                            "provider": "agenthub",
                            "model": execution["agent_name"],
                            "operation_type": "execution",
                            "cost": execution["agent_price_per_use"],
                            "input_tokens": None,
                            "output_tokens": None,
                            "duration_ms": None,
                            "created_at": execution["executed_at"],
                            "note": "Agent per-use pricing"
                        })
        
        # Calculate total charges for each month
        for month_data in monthly_data.values():
            # Sum execution charges
            execution_charges = sum(
                execution["charges"] for execution in month_data["executions"]
            )
            
            # Total charges = execution charges (container costs are calculated per hiring)
            month_data["total_charges"] = execution_charges
            
            # Calculate hiring charges (execution charges + their specific container costs)
            for hiring in month_data["hirings"]:
                # Get execution charges for this specific hiring
                hiring_execution_charges = sum(
                    execution["charges"] for execution in month_data["executions"]
                    if execution["hiring_id"] == hiring["id"]
                )
                
                # Get container costs for this specific hiring from the beginning of the month
                hiring_container_costs = 0.0
                try:
                    # Calculate container costs for this hiring from month start to now
                    month_start = datetime.strptime(month_data["month"], "%Y-%m").replace(tzinfo=timezone.utc)
                    month_end = datetime.now(timezone.utc)
                    
                    # Get container usage for this specific hiring
                    hiring_container_usage = db.query(ContainerResourceUsage).filter(
                        and_(
                            ContainerResourceUsage.hiring_id == hiring["id"],
                            ContainerResourceUsage.snapshot_timestamp >= month_start,
                            ContainerResourceUsage.snapshot_timestamp <= month_end
                        )
                    ).all()
                    
                    # Sum up container costs for this hiring
                    for usage in hiring_container_usage:
                        hiring_container_costs += usage.total_cost
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate container costs for hiring {hiring['id']}: {e}")
                    hiring_container_costs = 0.0
                
                # Total hiring charges = execution charges + container resource charges
                hiring["charges"] = hiring_execution_charges + hiring_container_costs
                
                # Add container cost breakdown for transparency
                hiring["container_costs"] = hiring_container_costs
                hiring["execution_costs"] = hiring_execution_charges
                
                # Update monthly total to include container costs
                month_data["total_charges"] += hiring_container_costs
        
        # Convert to list and sort by month
        result = list(monthly_data.values())
        result.sort(key=lambda x: x["month"], reverse=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching billing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch billing summary: {str(e)}"
        )


@router.get("/execution/{execution_id}/resources")
async def get_execution_resources(
    execution_id: str,
    user_id: int = Query(..., description="User ID to verify access"),
    db: Session = Depends(get_db)
):
    """Get detailed resource usage for a specific execution."""
    try:
        # Try to find execution by execution_id string first
        execution = db.query(Execution).filter(Execution.execution_id == execution_id).first()
        
        # If not found by execution_id, try by integer id
        if not execution:
            try:
                execution_id_int = int(execution_id)
                execution = db.query(Execution).filter(Execution.id == execution_id_int).first()
            except ValueError:
                pass
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Verify that the execution belongs to the requesting user
        if execution.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own executions"
            )
        
        # Get resource usage for this execution (using the integer id)
        resource_usage = db.query(ExecutionResourceUsage).filter(
            ExecutionResourceUsage.execution_id == execution.id
        ).all()
        
        # Get agent information
        agent_name = "Unknown Agent"
        agent_type = "unknown"
        deployment_id = None
        if execution.hiring_id:
            hiring = db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
            if hiring:
                agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                if agent:
                    agent_name = agent.name
                    agent_type = agent.agent_type
                
                # Get deployment information for container resources
                deployment = db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                if deployment:
                    deployment_id = deployment.deployment_id
        
        # Format resource usage data
        resources = []
        total_cost = 0.0
        
        for usage in resource_usage:
            resources.append({
                "id": usage.id,
                "resource_type": usage.resource_type,
                "provider": usage.resource_provider,
                "model": usage.resource_model,
                "operation_type": usage.operation_type,
                "cost": usage.cost,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "duration_ms": usage.duration_ms,
                "request_metadata": usage.request_metadata,
                "response_metadata": usage.response_metadata,
                "created_at": usage.created_at.isoformat() if usage.created_at else None
            })
            total_cost += usage.cost
        
        # Get container resource usage if deployment exists
        container_resources = None
        if deployment_id:
            try:
                enhanced_billing_service = EnhancedBillingService(db)
                container_costs = await enhanced_billing_service._get_container_resource_costs(
                    execution.user_id, 
                    execution.started_at or execution.created_at, 
                    execution.completed_at or execution.created_at
                )
                
                # Find the specific deployment
                for deployment in container_costs.get("deployments", []):
                    if deployment.get("deployment_id") == deployment_id:
                        container_resources = {
                            "deployment_id": deployment_id,
                            "cpu_hours": deployment.get("cpu_hours", 0.0),
                            "memory_gb_hours": deployment.get("memory_gb_hours", 0.0),
                            "storage_gb": deployment.get("storage_gb", 0.0),
                            "network_gb": deployment.get("network_gb", 0.0),
                            "container_cost": deployment.get("total_cost", 0.0),
                            "start_time": deployment.get("start_time"),
                            "end_time": deployment.get("end_time")
                        }
                        break
                        
            except Exception as e:
                logger.warning(f"Failed to get container resource costs for execution {execution_id}: {e}")
        
        return {
            "execution_id": execution.execution_id,  # Return the actual execution_id string
            "agent_name": agent_name,
            "agent_type": agent_type,
            "deployment_id": deployment_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "total_cost": total_cost,
            "resource_count": len(resources),
            "resources": resources,
            "container_resources": container_resources
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch execution resources: {str(e)}"
        )


@router.get("/hiring/{hiring_id}/resources")
async def get_hiring_resources(
    hiring_id: int,
    user_id: int = Query(..., description="User ID to verify access"),
    db: Session = Depends(get_db)
):
    """Get detailed resource usage for a specific hiring."""
    try:
        # Get hiring information
        hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
        
        if not hiring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hiring not found"
            )
        
        # Verify that the hiring belongs to the requesting user
        if hiring.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own hirings"
            )
        
        # Get agent information
        agent_name = "Unknown Agent"
        agent_type = "unknown"
        if hiring.agent:
            agent_name = hiring.agent.name
            agent_type = hiring.agent.agent_type
        
        # Get deployment information for container resources
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.hiring_id == hiring_id
        ).first()
        logger.info(f"Hiring {hiring_id} has deployment: {deployment is not None}")
        
        # Get all executions for this hiring
        executions = db.query(Execution).filter(Execution.hiring_id == hiring_id).all()
        logger.info(f"Hiring {hiring_id} has {len(executions)} executions")
        
        # Get resource usage for all executions
        total_cost = 0.0
        total_executions = len(executions)
        all_resources = []
        execution_charges = 0.0
        
        # Initialize execution charges to 0 if no executions
        if total_executions == 0:
            execution_charges = 0.0
        
        for execution in executions:
            logger.info(f"Checking execution {execution.id} (execution_id: {execution.execution_id})")
            resource_usage = db.query(ExecutionResourceUsage).filter(
                ExecutionResourceUsage.execution_id == execution.id
            ).all()
            logger.info(f"Execution {execution.id} has {len(resource_usage)} resource usage records")
            
            # Calculate execution cost from resource usage
            execution_cost = 0.0
            for usage in resource_usage:
                all_resources.append({
                    "execution_id": execution.execution_id,
                    "executed_at": execution.started_at.isoformat() if execution.started_at else None,
                    "resource_type": usage.resource_type,
                    "provider": usage.resource_provider,
                    "model": usage.resource_model,
                    "operation_type": usage.operation_type,
                    "cost": usage.cost,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                    "duration_ms": usage.duration_ms,
                    "request_metadata": usage.request_metadata,
                    "response_metadata": usage.response_metadata,
                    "created_at": usage.created_at.isoformat() if usage.created_at else None
                })
                execution_cost += usage.cost
                total_cost += usage.cost
            
            # Add agent per-use pricing if available
            if hasattr(hiring, 'agent') and hiring.agent and hasattr(hiring.agent, 'price_per_use') and hiring.agent.price_per_use:
                agent_execution_cost = hiring.agent.price_per_use
                execution_cost += agent_execution_cost
                total_cost += agent_execution_cost
                
                # Add agent pricing to resource usage for transparency
                all_resources.append({
                    "execution_id": execution.execution_id,
                    "executed_at": execution.started_at.isoformat() if execution.started_at else None,
                    "resource_type": "agent_execution",
                    "provider": "agenthub",
                    "model": hiring.agent.name,
                    "operation_type": "execution",
                    "cost": agent_execution_cost,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "duration_ms": None,
                    "request_metadata": None,
                    "response_metadata": None,
                    "created_at": execution.started_at.isoformat() if execution.started_at else None
                })
            
            execution_charges += execution_cost
        
        # Get container resource usage directly from database
        container_resources = None
        if deployment:
            logger.info(f"Getting container resource usage from database for deployment {deployment.deployment_id}")
            try:
                # Query container resource usage directly from database
                container_usage = db.query(ContainerResourceUsage).filter(
                    ContainerResourceUsage.deployment_id == deployment.deployment_id
                ).all()
                
                if container_usage:
                    # Calculate totals from raw database values
                    total_container_cost = sum(usage.total_cost for usage in container_usage)
                    
                    # Calculate resource usage totals from database
                    total_cpu_percent = sum(usage.cpu_usage_percent for usage in container_usage)
                    total_memory_bytes = sum(usage.memory_usage_bytes for usage in container_usage)
                    total_network_rx = sum(usage.network_rx_bytes for usage in container_usage)
                    total_network_tx = sum(usage.network_tx_bytes for usage in container_usage)
                    total_memory_limit = sum(usage.memory_limit_bytes for usage in container_usage)
                    
                    # Convert to appropriate units (same as database storage)
                    # CPU: convert percentage to hours (30-second intervals)
                    interval_hours = 30.0 / 3600.0  # 30 seconds in hours
                    total_cpu_hours = (total_cpu_percent / 100.0) * interval_hours
                    
                    # Memory: convert bytes to GB-hours
                    total_memory_gb_hours = (total_memory_bytes / (1024**3)) * interval_hours
                    
                    # Network: convert bytes to GB
                    total_network_gb = (total_network_rx + total_network_tx) / (1024**3)
                    
                    # Storage: convert memory limit bytes to GB-hours
                    total_storage_gb_hours = (total_memory_limit / (1024**3)) * interval_hours
                    
                    container_resources = {
                        "deployment_id": deployment.deployment_id,
                        "cpu_hours": round(total_cpu_hours, 4),
                        "memory_gb_hours": round(total_memory_gb_hours, 4),
                        "network_gb": round(total_network_gb, 4),
                        "storage_gb_hours": round(total_storage_gb_hours, 4),
                        "container_cost": round(total_container_cost, 6),
                        "snapshots_count": len(container_usage),
                        "start_time": min(usage.snapshot_timestamp for usage in container_usage).isoformat(),
                        "end_time": max(usage.snapshot_timestamp for usage in container_usage).isoformat()
                    }
                    
                    total_cost += total_container_cost
                    logger.info(f"Container resources from database: {container_resources}")
                else:
                    logger.info(f"No container usage data found for deployment {deployment.deployment_id}")
                    
            except Exception as e:
                logger.warning(f"Failed to get container resource usage from database for hiring {hiring_id}: {e}")
        else:
            logger.info(f"No deployment found for hiring {hiring_id}")
        
        return {
            "hiring_id": hiring_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": total_executions,
            "total_cost": total_cost,
            "execution_charges": round(execution_charges, 6),
            "resource_count": len(all_resources),
            "resources": all_resources,
            "container_resources": container_resources
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching hiring resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hiring resources: {str(e)}"
        )








@router.get("/invoice/{month}")
async def download_invoice(
    month: str,
    user_id: int = Query(..., description="User ID to verify access"),
    db: Session = Depends(get_db)
):
    """Download invoice for a specific month for a specific user."""
    try:
        # Verify that the user has data for this month
        # Calculate date range for the month
        try:
            year, month_num = month.split('-')
            start_date = datetime(int(year), int(month_num), 1)
            if int(month_num) == 12:
                end_date = datetime(int(year) + 1, 1, 1)
            else:
                end_date = datetime(int(year), int(month_num) + 1, 1)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Use YYYY-MM"
            )
        
        # Check if user has any executions or hirings in this month
        executions_count = db.query(Execution).filter(
            and_(
                Execution.created_at >= start_date,
                Execution.created_at < end_date,
                Execution.user_id == user_id
            )
        ).count()
        
        hirings_count = db.query(Hiring).filter(
            and_(
                Hiring.created_at >= start_date,
                Hiring.created_at < end_date,
                Hiring.user_id == user_id
            )
        ).count()
        
        # Note: We'll still generate an invoice even with no activity for transparency
        if executions_count == 0 and hirings_count == 0:
            logger.info(f"No billable activity found for user {user_id} in {month}, but will generate zero-amount invoice")
        
        # Get user information
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create invoice for this month
        invoice_service = InvoiceService(db)
        try:
            # Try to get existing invoice
            existing_invoices = await invoice_service.get_user_invoices(user_id, limit=100)
            invoice = None
            
            for inv in existing_invoices:
                if inv.get('billing_data', {}).get('billing_period', {}).get('start', '').startswith(month):
                    invoice = inv
                    break
            
            # If no invoice exists, create one
            if not invoice:
                try:
                    invoice = await invoice_service.create_monthly_invoice(
                        user_id=user_id,
                        month=month,
                        customer_email=user.email
                    )
                except Exception as invoice_error:
                    logger.warning(f"Could not create invoice through service: {invoice_error}")
                    # Create a basic invoice structure for PDF generation
                    invoice = {
                        'invoice_number': f"INV-{month}-{user_id:06d}-{datetime.now().strftime('%Y%m%d')}",
                        'status': 'draft',
                        'amount': 0.0,
                        'billing_data': {
                            'total_charges': 0.0,
                            'execution_count': executions_count,
                            'hirings_count': hirings_count,
                            'executions': [],
                            'hirings': [],
                            'billing_period': {
                                'start': start_date.isoformat(),
                                'end': end_date.isoformat()
                            }
                        }
                    }
        except Exception as e:
            logger.error(f"Failed to get/create invoice: {e}")
            # Create a basic invoice structure for PDF generation
            invoice = {
                'invoice_number': f"INV-{month}-{user_id:06d}-{datetime.now().strftime('%Y%m%d')}",
                'status': 'draft',
                'amount': 0.0,
                'billing_data': {
                    'total_charges': 0.0,
                    'execution_count': executions_count,
                    'hirings_count': hirings_count,
                    'executions': [],
                    'hirings': [],
                    'billing_period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    }
                }
            }
        
        # Generate PDF invoice
        try:
            from ..services.pdf_invoice_generator import PDFInvoiceGenerator
            
            pdf_generator = PDFInvoiceGenerator()
            user_data = {
                'username': user.username,
                'email': user.email
            }
            
            pdf_bytes = pdf_generator.generate_invoice_pdf(invoice, user_data)
            
            # Return PDF file
            from fastapi.responses import Response
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=invoice-{month}.pdf"
                }
            )
            
        except ImportError:
            logger.error("PDF generation dependencies not available")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF generation not available - missing dependencies"
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF invoice: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF invoice: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}"
        )

















@router.get("/payment-methods")
async def get_user_payment_methods(
    user_id: int = Query(..., description="User ID to get payment methods for"),
    db: Session = Depends(get_db)
):
    """Get all payment methods for a user"""
    try:
        if not PaymentConfig.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured"
            )
        
        payment_service = PaymentService(PaymentConfig.STRIPE_SECRET_KEY)
        
        # Get user's Stripe customer ID
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create Stripe customer
        customer = await payment_service._get_or_create_customer(user_id, user.email)
        
        # Get payment methods from Stripe
        payment_methods = await payment_service.get_customer_payment_methods(customer.id)
        
        return {
            "user_id": user_id,
            "payment_methods": payment_methods
        }
        
    except Exception as e:
        logger.error(f"Error fetching payment methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payment methods: {str(e)}"
        )


# ============================================================================
# Enhanced Billing Endpoints (Container Resource Cost Tracking)
# ============================================================================

@router.get("/enhanced/summary/{user_id}")
async def get_user_enhanced_billing_summary(
    user_id: int,
    months: int = Query(1, description="Number of months to fetch", ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive billing summary including container resource costs."""
    try:
        # Ensure user can only access their own billing or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own billing information"
            )
        
        billing_service = EnhancedBillingService(db)
        summary = await billing_service.get_user_billing_summary(user_id, months)
        
        if "error" in summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=summary["error"]
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced billing summary for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get enhanced billing summary: {str(e)}"
        )


@router.get("/enhanced/daily-usage/{user_id}")
async def get_user_daily_usage(
    user_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed daily usage for a specific user and date."""
    try:
        # Ensure user can only access their own usage or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own usage information"
            )
        
        # Parse date
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        billing_service = EnhancedBillingService(db)
        daily_usage = await billing_service.get_user_daily_usage(user_id, parsed_date)
        
        if "error" in daily_usage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=daily_usage["error"]
            )
        
        return daily_usage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily usage for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily usage: {str(e)}"
        )


@router.post("/enhanced/cost-estimate")
async def get_deployment_cost_estimate(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost estimate for a deployment before it starts."""
    try:
        billing_service = EnhancedBillingService(db)
        estimate = await billing_service.get_deployment_cost_estimate(
            request.deployment_type,
            request.duration_hours,
            request.avg_cpu_percent,
            request.avg_memory_gb
        )
        
        if "error" in estimate:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=estimate["error"]
            )
        
        return estimate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cost estimate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost estimate: {str(e)}"
        )


@router.get("/enhanced/budget-check/{user_id}")
async def check_budget_limit(
    user_id: int,
    estimated_cost: float = Query(..., description="Estimated cost to check against budget"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has sufficient budget for estimated costs."""
    try:
        # Ensure user can only access their own budget or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own budget information"
            )
        
        if estimated_cost < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estimated cost must be non-negative"
            )
        
        billing_service = EnhancedBillingService(db)
        budget_check = await billing_service.check_budget_limit(user_id, estimated_cost)
        
        return budget_check
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking budget for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check budget: {str(e)}"
        )


@router.get("/enhanced/monthly-breakdown/{user_id}")
async def get_monthly_breakdown(
    user_id: int,
    year: int = Query(..., description="Year to fetch"),
    month: int = Query(..., description="Month to fetch (1-12)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly billing breakdown for a specific user and month."""
    try:
        # Ensure user can only access their own billing or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own billing information"
            )
        
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12"
            )
        
        from ..services.resource_usage_tracker import ResourceUsageTracker
        resource_tracker = ResourceUsageTracker(db)
        monthly_billing = resource_tracker.get_user_monthly_billing(user_id, year, month)
        
        if not monthly_billing:
            return {
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
        
        return monthly_billing
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monthly breakdown for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monthly breakdown: {str(e)}"
        )


@router.get("/enhanced/deployment-costs/{deployment_id}")
async def get_deployment_costs(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed cost breakdown for a specific deployment."""
    try:
        from ..models.container_resource_usage import ContainerResourceUsage
        
        # Get deployment info
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        # Ensure user can only access their own deployments or is admin
        if deployment.hiring.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own deployments"
            )
        
        # Get resource usage for this deployment
        resource_usage = db.query(ContainerResourceUsage).filter(
            ContainerResourceUsage.deployment_id == deployment_id
        ).order_by(ContainerResourceUsage.snapshot_timestamp.desc()).all()
        
        if not resource_usage:
            return {
                "deployment_id": deployment_id,
                "agent_id": deployment.agent_id,
                "deployment_type": deployment.deployment_type,
                "total_cost": 0.0,
                "total_snapshots": 0,
                "cost_breakdown": {
                    "cpu_cost": 0.0,
                    "memory_cost": 0.0,
                    "network_cost": 0.0,
                    "storage_cost": 0.0
                },
                "resource_usage": {
                    "total_cpu_hours": 0.0,
                    "total_memory_gb_hours": 0.0,
                    "total_network_gb": 0.0
                },
                "snapshots": []
            }
        
        # Calculate totals
        total_cost = sum(r.total_cost for r in resource_usage)
        total_cpu_hours = sum(r.cpu_usage_percent for r in resource_usage) / 100.0 * (30/3600)
        total_memory_gb_hours = sum(r.memory_usage_bytes for r in resource_usage) / (1024**3) * (30/3600)
        total_network_gb = sum(r.network_rx_bytes + r.network_tx_bytes for r in resource_usage) / (1024**3)
        
        # Cost breakdown
        cost_breakdown = {
            "cpu_cost": sum(r.cpu_cost for r in resource_usage),
            "memory_cost": sum(r.memory_cost for r in resource_usage),
            "network_cost": sum(r.network_cost for r in resource_usage),
            "storage_cost": sum(r.storage_cost for r in resource_usage)
        }
        
        # Format snapshots
        snapshots = []
        for usage in resource_usage:
            snapshots.append({
                "timestamp": usage.snapshot_timestamp.isoformat(),
                "cpu_percent": usage.cpu_usage_percent,
                "memory_gb": usage.memory_usage_bytes / (1024**3),
                "network_gb": (usage.network_rx_bytes + usage.network_tx_bytes) / (1024**3),
                "total_cost": usage.total_cost,
                "container_status": usage.container_status
            })
        
        return {
            "deployment_id": deployment_id,
            "agent_id": deployment.agent_id,
            "deployment_type": deployment.deployment_type,
            "total_cost": round(total_cost, 6),
            "total_snapshots": len(resource_usage),
            "cost_breakdown": {
                "cpu_cost": round(cost_breakdown["cpu_cost"], 6),
                "memory_cost": round(cost_breakdown["memory_cost"], 6),
                "network_cost": round(cost_breakdown["network_cost"], 6),
                "storage_cost": round(cost_breakdown["storage_cost"], 6)
            },
            "resource_usage": {
                "total_cpu_hours": round(total_cpu_hours, 4),
                "total_memory_gb_hours": round(total_memory_gb_hours, 4),
                "total_network_gb": round(total_network_gb, 6)
            },
            "snapshots": snapshots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment costs for {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment costs: {str(e)}"
        )


@router.get("/enhanced/pricing")
async def get_resource_pricing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current resource pricing configuration."""
    try:
        from ..services.resource_usage_tracker import ResourceUsageTracker
        
        resource_tracker = ResourceUsageTracker(db)
        pricing = resource_tracker.pricing
        
        # Format pricing for API response
        formatted_pricing = {}
        for resource_type, deployment_pricing in pricing.items():
            formatted_pricing[resource_type] = {
                "unit": "per_hour" if resource_type in ["cpu", "memory", "storage"] else "per_gb",
                "deployment_types": deployment_pricing
            }
        
        return {
            "pricing": formatted_pricing,
            "currency": "USD",
            "billing_model": "AWS EC2-style hourly billing",
            "collection_interval": "30 seconds",
            "description": "Competitive pricing based on AWS EC2 rates"
        }
        
    except Exception as e:
        logger.error(f"Error getting resource pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resource pricing: {str(e)}"
        )


# ============================================================================
# Payment Methods Endpoints
# ============================================================================

@router.post("/payment-methods")
async def add_payment_method(
    request: AddPaymentMethodRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Add a new payment method for a user"""
    try:
        # Debug logging
        logger.info(f"Received payment method request: user_id={request.user_id}, payment_method_type={type(request.payment_method)}")
        logger.info(f"Payment method data: {request.payment_method}")
        
        if not PaymentConfig.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured"
            )
        
        payment_service = PaymentService(PaymentConfig.STRIPE_SECRET_KEY)
        
        # Get user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create Stripe customer
        customer = await payment_service._get_or_create_customer(request.user_id, user.email)
        
        # Create payment method in Stripe
        payment_method_result = await payment_service.create_payment_method(
            customer_id=customer.id,
            payment_method_data=request.payment_method
        )
        
        return {
            "success": True,
            "payment_method": payment_method_result
        }
        
    except ValueError as e:
        logger.error(f"Validation error adding payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error adding payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment method: {str(e)}"
        )


@router.post("/payment-methods/{payment_method_id}/default")
async def set_default_payment_method(
    payment_method_id: str,
    user_id: int = Query(..., description="User ID to verify access"),
    db: Session = Depends(get_db)
):
    """Set a payment method as default for a user"""
    try:
        if not PaymentConfig.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured"
            )
        
        payment_service = PaymentService(PaymentConfig.STRIPE_SECRET_KEY)
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create Stripe customer
        customer = await payment_service._get_or_create_customer(user_id, user.email)
        
        # Set as default payment method
        result = await payment_service.set_default_payment_method(
            customer_id=customer.id,
            payment_method_id=payment_method_id
        )
        
        return {
            "success": True,
            "message": "Default payment method updated"
        }
        
    except Exception as e:
        logger.error(f"Error setting default payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default payment method: {str(e)}"
        )


@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    user_id: int = Query(..., description="User ID to verify access"),
    db: Session = Depends(get_db)
):
    """Delete a payment method for a user"""
    try:
        if not PaymentConfig.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured"
            )
        
        payment_service = PaymentService(PaymentConfig.STRIPE_SECRET_KEY)
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create Stripe customer
        customer = await payment_service._get_or_create_customer(user_id, user.email)
        
        # Delete payment method from Stripe
        result = await payment_service.delete_payment_method(payment_method_id)
        
        return {
            "success": True,
            "message": "Payment method deleted"
        }
        
    except Exception as e:
        logger.error(f"Error deleting payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete payment method: {str(e)}"
        )