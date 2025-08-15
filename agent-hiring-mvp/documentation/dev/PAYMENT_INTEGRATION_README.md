# Payment Integration Guide

This guide explains how to set up and use the payment integration system in AgentHub, which allows users to pay invoices for their agent usage.

## 🚀 Overview

The payment system integrates with **Stripe** to provide:
- **Invoice Generation**: Automatic monthly invoices based on usage
- **Payment Processing**: Secure payment handling via Stripe
- **Webhook Integration**: Real-time payment status updates
- **Invoice Management**: View, cancel, and track invoice status

## 🛠️ Setup Instructions

### 1. Install Dependencies

The payment system requires the `stripe` package:

```bash
pip install stripe
```

Or add to your `requirements.txt`:
```txt
stripe
```

### 2. Configure Stripe

#### Get Stripe API Keys
1. Create a [Stripe account](https://stripe.com)
2. Go to the [Stripe Dashboard](https://dashboard.stripe.com)
3. Navigate to **Developers** → **API keys**
4. Copy your **Publishable key** and **Secret key**

#### Set Environment Variables
Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Payment Settings
DEFAULT_CURRENCY=usd
INVOICE_DUE_DAYS=30

# Company Billing Information
COMPANY_NAME=AgentHub
COMPANY_ADDRESS=123 Business St, City, State 12345
COMPANY_EMAIL=billing@agenthub.com
COMPANY_PHONE=+1-555-123-4567

# Invoice Settings
INVOICE_PREFIX=AH
AUTO_SEND_INVOICES=true
```

### 3. Configure Stripe Webhooks

1. In your Stripe Dashboard, go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Set the endpoint URL to: `https://yourdomain.com/api/v1/webhooks/stripe`
4. Select these events:
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `invoice.payment_action_required`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the webhook signing secret to your `.env` file

## 📊 How It Works

### Invoice Creation Flow
```
User Usage → Resource Tracking → Cost Calculation → Invoice Generation → Stripe Invoice → Payment Link
```

### Payment Processing Flow
```
User Clicks Pay → Stripe Checkout → Payment Processing → Webhook Notification → Status Update
```

## 🔌 API Endpoints

### Invoice Management

#### Create Monthly Invoice
```http
POST /api/v1/billing/invoice/{month}/create?user_id={user_id}
```

Creates a payable invoice for a specific month based on user's usage.

**Response:**
```json
{
  "success": true,
  "invoice_id": 123,
  "invoice_number": "AH-2024-01-000001-20240101",
  "amount": 25.50,
  "payment_url": "https://invoice.stripe.com/i/acct_...",
  "status": "sent",
  "due_date": "2024-02-01T00:00:00"
}
```

#### Get User Invoices
```http
GET /api/v1/billing/invoices?user_id={user_id}&limit=50
```

Returns all invoices for a user.

#### Get Invoice Details
```http
GET /api/v1/billing/invoice/{invoice_id}?user_id={user_id}
```

Returns detailed information about a specific invoice.

#### Process Payment
```http
POST /api/v1/billing/invoice/{invoice_id}/pay
Content-Type: application/json

{
  "payment_method_id": "pm_...",
  "user_id": 123
}
```

Processes payment for an invoice.

#### Cancel Invoice
```http
POST /api/v1/billing/invoice/{invoice_id}/cancel?user_id={user_id}
```

Cancels an unpaid invoice.

### Webhook Endpoints

#### Stripe Webhook
```http
POST /api/v1/webhooks/stripe
```

Handles Stripe webhook events for payment confirmations.

#### Webhook Health Check
```http
GET /api/v1/webhooks/health
```

Checks webhook configuration status.

## 💰 Usage Examples

### 1. Create an Invoice

```python
import requests

# Create invoice for January 2024
response = requests.post(
    "http://localhost:8000/api/v1/billing/invoice/2024-01/create",
    params={"user_id": 123}
)

if response.status_code == 200:
    invoice = response.json()
    print(f"Invoice created: {invoice['invoice_number']}")
    print(f"Payment URL: {invoice['payment_url']}")
```

### 2. Process Payment

```python
# Process payment using Stripe payment method
response = requests.post(
    "http://localhost:8000/api/v1/billing/invoice/123/pay",
    json={
        "payment_method_id": "pm_1234567890",
        "user_id": 123
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"Payment successful: {result['amount_paid']}")
```

### 3. Get Invoice Status

```python
# Get invoice details
response = requests.get(
    "http://localhost:8000/api/v1/billing/invoice/123",
    params={"user_id": 123}
)

if response.status_code == 200:
    invoice = response.json()
    print(f"Status: {invoice['status']}")
    print(f"Amount: ${invoice['amount']}")
    print(f"Paid: {invoice['is_paid']}")
```

## 🔧 Frontend Integration

### React Component Example

```tsx
import React, { useState } from 'react';

const InvoicePayment = ({ invoiceId, amount, paymentUrl }) => {
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    setLoading(true);
    
    try {
      // Redirect to Stripe hosted invoice page
      window.open(paymentUrl, '_blank');
    } catch (error) {
      console.error('Payment failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="invoice-payment">
      <h3>Invoice Payment</h3>
      <p>Amount: ${amount}</p>
      <button 
        onClick={handlePayment}
        disabled={loading}
        className="btn btn-primary"
      >
        {loading ? 'Processing...' : 'Pay Now'}
      </button>
    </div>
  );
};
```

## 🧪 Testing

### Run Payment Integration Tests

```bash
python test_payment_integration.py
```

This will test:
- Configuration loading
- Payment service initialization
- Invoice service functionality
- API endpoint availability

### Test with Stripe Test Keys

1. Use Stripe test keys (start with `sk_test_`)
2. Use Stripe test card numbers:
   - **Success**: `4242 4242 4242 4242`
   - **Decline**: `4000 0000 0000 0002`
   - **Requires Authentication**: `4000 0025 0000 3155`

## 🚨 Troubleshooting

### Common Issues

#### 1. "Invalid API key" Error
- Check your `STRIPE_SECRET_KEY` in `.env`
- Ensure you're using the correct key (test vs live)
- Verify the key format starts with `sk_test_` or `sk_live_`

#### 2. Webhook Signature Verification Failed
- Check your `STRIPE_WEBHOOK_SECRET`
- Ensure webhook endpoint URL is correct
- Verify webhook events are properly configured

#### 3. Invoice Creation Fails
- Check database connection
- Verify user exists
- Ensure billing data is available for the month

#### 4. Payment Processing Errors
- Check Stripe dashboard for error details
- Verify payment method is valid
- Check invoice status in database

### Debug Mode

Enable debug logging by setting:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/server"
python -c "
from server.config.payment_config import PaymentConfig
PaymentConfig.validate_config()
"
```

## 🔒 Security Considerations

### API Key Security
- Never commit API keys to version control
- Use environment variables for all sensitive data
- Rotate keys regularly
- Use test keys for development

### Webhook Security
- Always verify webhook signatures
- Use HTTPS in production
- Implement rate limiting
- Log all webhook events

### Data Privacy
- Encrypt sensitive payment data
- Implement proper access controls
- Follow PCI DSS guidelines
- Regular security audits

## 📈 Monitoring & Analytics

### Stripe Dashboard
- Monitor payment success rates
- Track revenue and refunds
- View customer analytics
- Set up alerts for failures

### Application Logs
- Payment processing logs
- Webhook event logs
- Error tracking
- Performance metrics

### Database Monitoring
- Invoice status tracking
- Payment history
- User billing patterns
- Revenue analytics

## 🚀 Production Deployment

### Environment Setup
1. Use live Stripe keys
2. Set up production webhook endpoints
3. Configure proper SSL certificates
4. Set up monitoring and alerting

### Scaling Considerations
- Database connection pooling
- Async payment processing
- Webhook queue management
- Load balancing for webhooks

### Backup & Recovery
- Regular database backups
- Webhook event replay capability
- Payment reconciliation tools
- Disaster recovery procedures

## 📚 Additional Resources

- [Stripe Documentation](https://stripe.com/docs)
- [Stripe API Reference](https://stripe.com/docs/api)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [PCI Compliance](https://stripe.com/docs/security)
- [Stripe Testing](https://stripe.com/docs/testing)

## 🤝 Support

For issues with the payment integration:

1. Check the troubleshooting section above
2. Review Stripe dashboard for errors
3. Check application logs
4. Run the test script
5. Contact the development team

---

**Happy Billing! 💰✨**
