"""
Payment service for handling Stripe integration and invoice management.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Conditional import for Stripe
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

logger = logging.getLogger(__name__)

class PaymentService:
    """Handles Stripe payment processing and invoice management"""
    
    def __init__(self, stripe_secret_key: str):
        if not STRIPE_AVAILABLE:
            raise ImportError("Stripe is not installed. Please install it with: pip install stripe")
        
        if not stripe_secret_key:
            raise ValueError("Stripe secret key is required")
            
        stripe.api_key = stripe_secret_key

    async def create_payment_method(self, customer_id: str, payment_method_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment method for a customer"""
        try:
            # Check if we're using a test token or raw card data
            if 'token' in payment_method_data:
                # Using Stripe test token - correct format: card[token]=tok_visa
                payment_method = stripe.PaymentMethod.create(
                    type='card',
                    card={
                        'token': payment_method_data['token']
                    },
                    billing_details={
                        'name': payment_method_data.get('billing_details', {}).get('name'),
                        'address': payment_method_data.get('billing_details', {}).get('address', {})
                    }
                )
            else:
                # Using raw card data (requires special Stripe configuration)
                payment_method = stripe.PaymentMethod.create(
                    type='card',
                    card={
                        'number': payment_method_data['card']['number'],
                        'exp_month': payment_method_data['card']['exp_month'],
                        'exp_year': payment_method_data['card']['exp_year'],
                        'cvc': payment_method_data['card']['cvc']
                    },
                    billing_details={
                        'name': payment_method_data.get('billing_details', {}).get('name'),
                        'address': payment_method_data.get('billing_details', {}).get('address', {})
                    }
                )
            
            # Attach to customer
            payment_method.attach(customer=customer_id)
            
            # Get the updated payment method with customer info
            payment_method = stripe.PaymentMethod.retrieve(payment_method.id)
            
            logger.info(f"Created payment method {payment_method.id} for customer {customer_id}")
            
            return {
                'id': payment_method.id,
                'type': payment_method.type,
                'card': {
                    'brand': payment_method.card.brand,
                    'last4': payment_method.card.last4,
                    'exp_month': payment_method.card.exp_month,
                    'exp_year': payment_method.card.exp_year
                },
                'is_default': False,  # New payment methods are not default by default
                'created_at': datetime.fromtimestamp(payment_method.created).isoformat()
            }
            
        except stripe.error.CardError as e:
            logger.error(f"Card error creating payment method: {str(e)}")
            raise Exception(f"Card error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create payment method: {str(e)}")
            raise Exception(f"Failed to create payment method: {str(e)}")

    async def get_customer_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )
            
            # Get customer to check default payment method
            customer = stripe.Customer.retrieve(customer_id)
            default_payment_method_id = customer.invoice_settings.default_payment_method
            
            result = []
            for pm in payment_methods.data:
                result.append({
                    'id': pm.id,
                    'type': pm.type,
                    'card': {
                        'brand': pm.card.brand,
                        'last4': pm.card.last4,
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year
                    },
                    'is_default': pm.id == default_payment_method_id,
                    'created_at': datetime.fromtimestamp(pm.created).isoformat()
                })
            
            logger.info(f"Retrieved {len(result)} payment methods for customer {customer_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get payment methods for customer {customer_id}: {str(e)}")
            raise Exception(f"Failed to get payment methods: {str(e)}")

    async def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> Dict[str, Any]:
        """Set a payment method as default for a customer"""
        try:
            # Update customer's default payment method
            customer = stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            
            logger.info(f"Set payment method {payment_method_id} as default for customer {customer_id}")
            
            return {
                'success': True,
                'customer_id': customer_id,
                'default_payment_method': payment_method_id
            }
            
        except Exception as e:
            logger.error(f"Failed to set default payment method {payment_method_id} for customer {customer_id}: {str(e)}")
            raise Exception(f"Failed to set default payment method: {str(e)}")

    async def delete_payment_method(self, payment_method_id: str) -> Dict[str, Any]:
        """Delete a payment method"""
        try:
            # Detach the payment method (this removes it from the customer)
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            
            logger.info(f"Deleted payment method {payment_method_id}")
            
            return {
                'success': True,
                'payment_method_id': payment_method_id
            }
            
        except Exception as e:
            logger.error(f"Failed to delete payment method {payment_method_id}: {str(e)}")
            raise Exception(f"Failed to delete payment method: {str(e)}")

    async def create_invoice(self, user_id: int, amount: float, description: str, customer_email: str = None) -> Dict[str, Any]:
        """Create a Stripe invoice for a user"""
        try:
            # Create or get customer
            customer = await self._get_or_create_customer(user_id, customer_email)
            
            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer.id,
                description=description,
                auto_advance=False,  # Don't auto-finalize
                collection_method='send_invoice',  # Send invoice to customer
                days_until_due=30  # 30 days to pay
            )
            
            # Add invoice item
            stripe.InvoiceItem.create(
                customer=customer.id,
                invoice=invoice.id,
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                description=description
            )
            
            # Finalize the invoice
            invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            # Send the invoice to customer
            invoice = stripe.Invoice.send_invoice(invoice.id)
            
            logger.info(f"Created Stripe invoice {invoice.id} for user {user_id}, amount: ${amount}")
            
            return {
                'invoice_id': invoice.id,
                'customer_id': customer.id,
                'amount': amount,
                'status': invoice.status,
                'hosted_invoice_url': invoice.hosted_invoice_url,
                'invoice_pdf': invoice.invoice_pdf,
                'due_date': datetime.fromtimestamp(invoice.due_date) if invoice.due_date else None
            }
        except Exception as e:
            logger.error(f"Failed to create Stripe invoice: {str(e)}")
            raise Exception(f"Failed to create invoice: {str(e)}")
    
    async def process_payment(self, invoice_id: str, payment_method_id: str) -> Dict[str, Any]:
        """Process payment for an invoice"""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            
            # Pay the invoice with the specified payment method
            invoice = stripe.Invoice.pay(
                invoice_id,
                payment_method=payment_method_id
            )
            
            logger.info(f"Successfully processed payment for invoice {invoice_id}")
            
            return {
                'invoice_id': invoice.id,
                'status': invoice.status,
                'paid': invoice.paid,
                'amount_paid': invoice.amount_paid / 100,
                'payment_intent': invoice.payment_intent
            }
        except stripe.error.CardError as e:
            logger.error(f"Card error for invoice {invoice_id}: {str(e)}")
            raise Exception(f"Card error: {str(e)}")
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid request for invoice {invoice_id}: {str(e)}")
            raise Exception(f"Invalid request: {str(e)}")
        except Exception as e:
            logger.error(f"Payment failed for invoice {invoice_id}: {str(e)}")
            raise Exception(f"Payment failed: {str(e)}")
    
    async def get_invoice_status(self, invoice_id: str) -> Dict[str, Any]:
        """Get current status of an invoice"""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            
            return {
                'invoice_id': invoice.id,
                'status': invoice.status,
                'paid': invoice.paid,
                'amount_due': invoice.amount_due / 100,
                'amount_paid': invoice.amount_paid / 100,
                'due_date': datetime.fromtimestamp(invoice.due_date) if invoice.due_date else None,
                'hosted_invoice_url': invoice.hosted_invoice_url,
                'invoice_pdf': invoice.invoice_pdf
            }
        except Exception as e:
            logger.error(f"Failed to get invoice status for {invoice_id}: {str(e)}")
            raise Exception(f"Failed to get invoice status: {str(e)}")
    
    async def create_payment_intent(self, amount: float, customer_id: str, description: str) -> Dict[str, Any]:
        """Create a payment intent for immediate payment"""
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                customer=customer_id,
                description=description,
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
            logger.info(f"Created payment intent {payment_intent.id} for customer {customer_id}")
            
            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': amount,
                'status': payment_intent.status
            }
        except Exception as e:
            logger.error(f"Failed to create payment intent: {str(e)}")
            raise Exception(f"Failed to create payment intent: {str(e)}")
    
    async def _get_or_create_customer(self, user_id: int, customer_email: str = None):
        """Get existing Stripe customer or create new one"""
        try:
            # First try to find existing customer by email (more reliable than metadata search)
            if customer_email:
                customers = stripe.Customer.list(
                    limit=100,
                    email=customer_email
                )
                
                if customers.data:
                    # Update existing customer with user_id metadata if not present
                    customer = customers.data[0]
                    if not customer.metadata.get('user_id'):
                        stripe.Customer.modify(
                            customer.id,
                            metadata={'user_id': str(user_id)}
                        )
                    return customer
            
            # Create new customer if not found
            customer_data = {
                'metadata': {'user_id': str(user_id)},
                'description': f'AgentHub User {user_id}'
            }
            
            if customer_email:
                customer_data['email'] = customer_email
            
            customer = stripe.Customer.create(**customer_data)
            logger.info(f"Created new Stripe customer {customer.id} for user {user_id}")
            
            return customer
            
        except Exception as e:
            logger.error(f"Failed to get or create customer for user {user_id}: {str(e)}")
            raise Exception(f"Failed to manage customer: {str(e)}")
    
    async def refund_payment(self, payment_intent_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a payment"""
        try:
            refund_data = {'payment_intent': payment_intent_id}
            
            if amount:
                refund_data['amount'] = int(amount * 100)  # Convert to cents
            
            refund = stripe.Refund.create(**refund_data)
            
            logger.info(f"Created refund {refund.id} for payment intent {payment_intent_id}")
            
            return {
                'refund_id': refund.id,
                'amount': refund.amount / 100,
                'status': refund.status,
                'reason': refund.reason
            }
        except Exception as e:
            logger.error(f"Failed to create refund for payment intent {payment_intent_id}: {str(e)}")
            raise Exception(f"Failed to create refund: {str(e)}")
