"""
Invoice service for managing invoice creation, payment tracking, and business logic.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.invoice import Invoice
from ..models.user import User
from ..models.execution import Execution
from ..models.hiring import Hiring
from ..models.agent import Agent
from ..models.resource_usage import ExecutionResourceUsage
from ..config.payment_config import PaymentConfig
try:
    from .payment_service import PaymentService
    PAYMENT_SERVICE_AVAILABLE = True
except ImportError:
    PAYMENT_SERVICE_AVAILABLE = False
    PaymentService = None

logger = logging.getLogger(__name__)

class InvoiceService:
    """Handles invoice creation, management, and payment tracking"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        if PAYMENT_SERVICE_AVAILABLE and PaymentConfig.STRIPE_SECRET_KEY:
            try:
                self.payment_service = PaymentService(PaymentConfig.STRIPE_SECRET_KEY)
            except Exception as e:
                logger.warning(f"Payment service initialization failed: {e}")
                self.payment_service = None
        else:
            self.payment_service = None
            logger.warning("Payment service not available - Stripe not configured or not installed")
    
    async def create_monthly_invoice(self, user_id: int, month: str, customer_email: str = None) -> Dict[str, Any]:
        """Create a monthly invoice for a user based on their usage"""
        try:
            # Parse month (format: YYYY-MM)
            year, month_num = month.split('-')
            start_date = datetime(int(year), int(month_num), 1, tzinfo=timezone.utc)
            
            if int(month_num) == 12:
                end_date = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end_date = datetime(int(year), int(month_num) + 1, 1, tzinfo=timezone.utc)
            
            # Get user's billing data for the month
            billing_data = await self._get_monthly_billing_data(user_id, start_date, end_date)
            
            if not billing_data or billing_data['total_charges'] <= 0:
                raise ValueError(f"No billable activity found for {month}")
            
            # Generate invoice number
            invoice_number = self._generate_invoice_number(user_id, month)
            
            # Create invoice record in database
            invoice = Invoice(
                invoice_number=invoice_number,
                user_id=user_id,
                amount=billing_data['total_charges'],
                currency=PaymentConfig.DEFAULT_CURRENCY.upper(),
                status='draft',
                description=f"AgentHub Usage - {month}",
                billing_period_start=start_date,
                billing_period_end=end_date,
                due_date=datetime.now(timezone.utc) + timedelta(days=PaymentConfig.INVOICE_DUE_DAYS),
                invoice_data=json.dumps(billing_data)
            )
            
            self.db.add(invoice)
            self.db.commit()
            self.db.refresh(invoice)
            
            # Create Stripe invoice if payment service is available
            if self.payment_service:
                try:
                    stripe_invoice = await self.payment_service.create_invoice(
                        user_id=user_id,
                        amount=billing_data['total_charges'],
                        description=f"AgentHub Usage - {month}",
                        customer_email=customer_email
                    )
                    
                    # Update invoice with Stripe information
                    invoice.stripe_invoice_id = stripe_invoice['invoice_id']
                    invoice.status = 'sent'
                    self.db.commit()
                    
                    logger.info(f"Created Stripe invoice {stripe_invoice['invoice_id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to create Stripe invoice: {e}")
                    # Continue without Stripe integration
                    invoice.status = 'draft'
                    self.db.commit()
            else:
                # No payment service available, mark as draft
                invoice.status = 'draft'
                self.db.commit()
                logger.warning("Payment service not available, invoice created as draft")
            
            logger.info(f"Created invoice {invoice_number} for user {user_id}, month {month}, amount: ${billing_data['total_charges']}")
            
            # Prepare response
            response = {
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount': invoice.amount,
                'status': invoice.status,
                'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                'billing_data': billing_data
            }
            
            # Add Stripe-specific fields if available
            if self.payment_service and invoice.stripe_invoice_id:
                response.update({
                    'stripe_invoice_id': invoice.stripe_invoice_id,
                    'payment_url': stripe_invoice.get('hosted_invoice_url') if 'stripe_invoice' in locals() else None
                })
            else:
                response.update({
                    'stripe_invoice_id': None,
                    'payment_url': None,
                    'note': 'Payment processing not available'
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create monthly invoice for user {user_id}, month {month}: {str(e)}")
            self.db.rollback()
            raise
    
    async def get_user_invoices(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all invoices for a user"""
        try:
            invoices = self.db.query(Invoice).filter(
                Invoice.user_id == user_id
            ).order_by(Invoice.created_at.desc()).limit(limit).all()
            
            return [invoice.to_dict() for invoice in invoices]
            
        except Exception as e:
            logger.error(f"Failed to get invoices for user {user_id}: {str(e)}")
            raise
    
    async def get_invoice_details(self, invoice_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed invoice information"""
        try:
            invoice = self.db.query(Invoice).filter(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.user_id == user_id
                )
            ).first()
            
            if not invoice:
                return None
            
            # Get Stripe invoice status if available
            stripe_status = None
            if self.payment_service and invoice.stripe_invoice_id:
                try:
                    stripe_status = await self.payment_service.get_invoice_status(invoice.stripe_invoice_id)
                except Exception as e:
                    logger.warning(f"Failed to get Stripe status for invoice {invoice_id}: {str(e)}")
            
            result = invoice.to_dict()
            if stripe_status:
                result['stripe_status'] = stripe_status
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get invoice details for {invoice_id}: {str(e)}")
            raise
    
    async def process_payment(self, invoice_id: int, user_id: int, payment_method_id: str) -> Dict[str, Any]:
        """Process payment for an invoice"""
        try:
            invoice = self.db.query(Invoice).filter(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.user_id == user_id
                )
            ).first()
            
            if not invoice:
                raise ValueError("Invoice not found")
            
            if invoice.status == 'paid':
                raise ValueError("Invoice is already paid")
            
            if not self.payment_service:
                raise ValueError("Payment service not available - Stripe not configured")
            
            if not invoice.stripe_invoice_id:
                raise ValueError("Invoice not linked to Stripe")
            
            # Process payment through Stripe
            payment_result = await self.payment_service.process_payment(
                invoice.stripe_invoice_id,
                payment_method_id
            )
            
            # Update invoice status
            invoice.status = 'paid'
            invoice.payment_method_id = payment_method_id
            invoice.payment_intent_id = payment_result.get('payment_intent')
            invoice.paid_at = datetime.now(timezone.utc)
            invoice.amount_paid = payment_result['amount_paid']
            
            self.db.commit()
            
            logger.info(f"Successfully processed payment for invoice {invoice.invoice_number}")
            
            return {
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount_paid': payment_result['amount_paid'],
                'status': 'paid',
                'paid_at': invoice.paid_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Payment processing failed for invoice {invoice_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def cancel_invoice(self, invoice_id: int, user_id: int) -> Dict[str, Any]:
        """Cancel an unpaid invoice"""
        try:
            invoice = self.db.query(Invoice).filter(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.user_id == user_id
                )
            ).first()
            
            if not invoice:
                raise ValueError("Invoice not found")
            
            if invoice.status == 'paid':
                raise ValueError("Cannot cancel paid invoice")
            
            invoice.status = 'cancelled'
            self.db.commit()
            
            logger.info(f"Cancelled invoice {invoice.invoice_number}")
            
            return {
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'status': 'cancelled'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel invoice {invoice_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def _get_monthly_billing_data(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get billing data for a specific month"""
        try:
            # Get executions for this user in the date range
            executions = self.db.query(Execution).filter(
                and_(
                    Execution.user_id == user_id,
                    Execution.created_at >= start_date,
                    Execution.created_at < end_date
                )
            ).all()
            
            total_charges = 0.0
            execution_details = []
            
            for execution in executions:
                # Get resource usage for this execution
                resource_usage = self.db.query(ExecutionResourceUsage).filter(
                    ExecutionResourceUsage.execution_id == execution.id
                ).all()
                
                execution_cost = sum(usage.cost for usage in resource_usage)
                total_charges += execution_cost
                
                # Get agent name
                agent_name = "Unknown Agent"
                if execution.hiring_id:
                    hiring = self.db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
                    if hiring:
                        agent = self.db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                        if agent:
                            agent_name = agent.name
                
                execution_details.append({
                    'execution_id': execution.execution_id,
                    'agent_name': agent_name,
                    'cost': execution_cost,
                    'created_at': execution.created_at.isoformat(),
                    'resource_usage': [
                        {
                            'resource_type': usage.resource_type,
                            'provider': usage.resource_provider,
                            'cost': usage.cost,
                            'input_tokens': usage.input_tokens,
                            'output_tokens': usage.output_tokens
                        }
                        for usage in resource_usage
                    ]
                })
            
            return {
                'total_charges': total_charges,
                'execution_count': len(executions),
                'executions': execution_details,
                'billing_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get monthly billing data for user {user_id}: {str(e)}")
            raise
    
    def _generate_invoice_number(self, user_id: int, month: str) -> str:
        """Generate a unique invoice number"""
        prefix = PaymentConfig.INVOICE_PREFIX
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{prefix}-{month}-{user_id:06d}-{timestamp}"
    
    async def get_overdue_invoices(self) -> List[Dict[str, Any]]:
        """Get all overdue invoices across all users"""
        try:
            overdue_invoices = self.db.query(Invoice).filter(
                and_(
                    Invoice.status.in_(['sent', 'draft']),
                    Invoice.due_date < datetime.now(timezone.utc)
                )
            ).all()
            
            return [invoice.to_dict() for invoice in overdue_invoices]
            
        except Exception as e:
            logger.error(f"Failed to get overdue invoices: {str(e)}")
            raise
    
    async def send_payment_reminders(self) -> Dict[str, Any]:
        """Send payment reminders for overdue invoices"""
        try:
            overdue_invoices = await self.get_overdue_invoices()
            
            reminders_sent = 0
            for invoice_data in overdue_invoices:
                try:
                    # Update status to overdue
                    invoice = self.db.query(Invoice).filter(Invoice.id == invoice_data['id']).first()
                    if invoice and invoice.status != 'overdue':
                        invoice.status = 'overdue'
                        self.db.commit()
                    
                    # TODO: Send email reminder
                    # This would integrate with your email service
                    
                    reminders_sent += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send reminder for invoice {invoice_data['id']}: {str(e)}")
                    continue
            
            logger.info(f"Sent {reminders_sent} payment reminders")
            
            return {
                'reminders_sent': reminders_sent,
                'total_overdue': len(overdue_invoices)
            }
            
        except Exception as e:
            logger.error(f"Failed to send payment reminders: {str(e)}")
            raise
