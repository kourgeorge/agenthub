"""Webhook endpoints for external service integrations."""

import logging
import json
import stripe
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.invoice import Invoice
from ..config.payment_config import PaymentConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    try:
        # Get the webhook payload
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature header"
            )
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, PaymentConfig.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
        
        # Handle the event
        if event['type'] == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event['data']['object'], db)
        elif event['type'] == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event['data']['object'], db)
        elif event['type'] == 'invoice.payment_action_required':
            await handle_invoice_payment_action_required(event['data']['object'], db)
        elif event['type'] == 'customer.subscription.created':
            await handle_subscription_created(event['data']['object'], db)
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event['data']['object'], db)
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event['data']['object'], db)
        else:
            logger.info(f"Unhandled event type: {event['type']}")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def handle_invoice_payment_succeeded(invoice_data: Dict[str, Any], db: Session):
    """Handle successful invoice payment"""
    try:
        stripe_invoice_id = invoice_data['id']
        
        # Find corresponding invoice in our database
        invoice = db.query(Invoice).filter(
            Invoice.stripe_invoice_id == stripe_invoice_id
        ).first()
        
        if not invoice:
            logger.warning(f"No invoice found for Stripe invoice {stripe_invoice_id}")
            return
        
        # Update invoice status
        invoice.status = 'paid'
        invoice.paid_at = stripe.utils.convert_tstamp(invoice_data.get('status_transitions', {}).get('paid_at'))
        invoice.amount_paid = invoice_data.get('amount_paid', 0) / 100  # Convert from cents
        
        # Update payment intent if available
        if invoice_data.get('payment_intent'):
            invoice.payment_intent_id = invoice_data['payment_intent']
        
        # Update invoice data with payment information
        if hasattr(invoice, 'invoice_data') and invoice.invoice_data:
            try:
                data = json.loads(invoice.invoice_data)
                data['payment_processed_at'] = datetime.now(timezone.utc).isoformat()
                data['stripe_payment_intent'] = invoice_data.get('payment_intent')
                invoice.invoice_data = json.dumps(data)
            except (json.JSONDecodeError, AttributeError):
                pass
        
        db.commit()
        
        logger.info(f"Updated invoice {invoice.invoice_number} to paid status")
        
        # TODO: Send payment confirmation email
        # TODO: Update user billing status
        # TODO: Trigger any post-payment workflows
        
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {e}")
        db.rollback()


async def handle_invoice_payment_failed(invoice_data: Dict[str, Any], db: Session):
    """Handle failed invoice payment"""
    try:
        stripe_invoice_id = invoice_data['id']
        
        # Find corresponding invoice in our database
        invoice = db.query(Invoice).filter(
            Invoice.stripe_invoice_id == stripe_invoice_id
        ).first()
        
        if not invoice:
            logger.warning(f"No invoice found for Stripe invoice {stripe_invoice_id}")
            return
        
        # Update invoice status
        invoice.status = 'payment_failed'
        db.commit()
        
        logger.info(f"Updated invoice {invoice.invoice_number} to payment_failed status")
        
        # TODO: Send payment failure notification
        # TODO: Implement retry logic
        
    except Exception as e:
        logger.error(f"Error handling payment failed: {e}")
        db.rollback()


async def handle_invoice_payment_action_required(invoice_data: Dict[str, Any], db: Session):
    """Handle invoice requiring payment action"""
    try:
        stripe_invoice_id = invoice_data['id']
        
        # Find corresponding invoice in our database
        invoice = db.query(Invoice).filter(
            Invoice.stripe_invoice_id == stripe_invoice_id
        ).first()
        
        if not invoice:
            logger.warning(f"No invoice found for Stripe invoice {stripe_invoice_id}")
            return
        
        # Update invoice status
        invoice.status = 'action_required'
        db.commit()
        
        logger.info(f"Updated invoice {invoice.invoice_number} to action_required status")
        
        # TODO: Send notification about required action
        
    except Exception as e:
        logger.error(f"Error handling payment action required: {e}")
        db.rollback()


async def handle_subscription_created(subscription_data: Dict[str, Any], db: Session):
    """Handle new subscription creation"""
    try:
        logger.info(f"New subscription created: {subscription_data['id']}")
        
        # TODO: Implement subscription management
        # TODO: Create recurring billing records
        
    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")


async def handle_subscription_updated(subscription_data: Dict[str, Any], db: Session):
    """Handle subscription updates"""
    try:
        logger.info(f"Subscription updated: {subscription_data['id']}")
        
        # TODO: Update subscription status
        # TODO: Handle plan changes
        
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")


async def handle_subscription_deleted(subscription_data: Dict[str, Any], db: Session):
    """Handle subscription deletion"""
    try:
        logger.info(f"Subscription deleted: {subscription_data['id']}")
        
        # TODO: Handle subscription cancellation
        # TODO: Update billing status
        
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhooks"""
    return {
        "status": "healthy",
        "webhooks": {
            "stripe": "enabled" if PaymentConfig.STRIPE_WEBHOOK_SECRET else "disabled"
        }
    }
