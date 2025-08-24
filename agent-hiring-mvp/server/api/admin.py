"""Admin API endpoints for viewing customer billing data."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ..database import get_db
from ..models.user import User
from ..models.invoice import Invoice
from ..models.execution import Execution
from ..middleware.auth import get_current_user
from ..middleware.permissions import require_admin_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/billing/customers")
@require_admin_permission("view")
async def get_all_customer_billing(
    limit: int = Query(100, description="Maximum number of customers to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing summary for all customers (admin only)."""
    try:
        # Get all users with billing data
        customers = db.query(User).filter(User.is_active == True).limit(limit).all()
        
        customer_billing = []
        for customer in customers:
            # Get customer's invoices
            invoices = db.query(Invoice).filter(Invoice.user_id == customer.id).all()
            
            # Calculate totals
            total_invoiced = sum(invoice.amount for invoice in invoices)
            total_paid = sum(invoice.amount_paid for invoice in invoices)
            total_outstanding = total_invoiced - total_paid
            
            customer_billing.append({
                "user_id": customer.id,
                "email": customer.email,
                "username": customer.username,
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding,
                "invoice_count": len(invoices)
            })
        
        return {
            "total_customers": len(customer_billing),
            "customers": customer_billing
        }
        
    except Exception as e:
        logger.error(f"Error fetching customer billing data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customer billing data: {str(e)}"
        )
