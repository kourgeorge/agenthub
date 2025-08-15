# Payment Integration Setup Guide

## 🚀 Quick Start

### 1. Install Stripe (Required for Payment Processing)

```bash
pip install stripe
```

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Payment Settings
DEFAULT_CURRENCY=usd
INVOICE_DUE_DAYS=30

# Company Information
COMPANY_NAME=AgentHub
COMPANY_ADDRESS=123 Business St, City, State 12345
COMPANY_EMAIL=billing@agenthub.com
COMPANY_PHONE=+1-555-123-4567

# Invoice Settings
INVOICE_PREFIX=AH
AUTO_SEND_INVOICES=true
```

### 3. Get Stripe API Keys

1. Create a [Stripe account](https://stripe.com)
2. Go to [Stripe Dashboard](https://dashboard.stripe.com)
3. Navigate to **Developers** → **API keys**
4. Copy your keys (use test keys for development)

### 4. Test the Integration

```bash
python test_payment_integration.py
```

## 🔧 What's Implemented

### ✅ Core Features
- **Invoice Generation**: Automatic monthly invoices based on usage
- **Payment Processing**: Stripe integration for secure payments
- **Webhook Handling**: Real-time payment status updates
- **Invoice Management**: View, cancel, and track invoices

### ✅ API Endpoints
- `POST /api/v1/billing/invoice/{month}/create` - Create monthly invoice
- `POST /api/v1/billing/invoice/{invoice_id}/pay` - Process payment
- `GET /api/v1/billing/invoices` - Get user invoices
- `GET /api/v1/billing/invoice/{invoice_id}` - Get invoice details
- `POST /api/v1/billing/invoice/{invoice_id}/cancel` - Cancel invoice
- `POST /api/v1/webhooks/stripe` - Stripe webhook handler

### ✅ Database Models
- **Invoice**: Stores invoice information and payment status
- **User**: Updated with invoice relationship

## 🚨 Current Status

The payment system is **partially implemented**:

- ✅ **Database models** - Ready
- ✅ **API endpoints** - Ready  
- ✅ **Invoice service** - Ready
- ✅ **Payment service** - Ready
- ❌ **Stripe integration** - Requires API keys
- ❌ **Webhook setup** - Requires Stripe configuration

## 🔍 Troubleshooting

### Server Won't Start
```bash
# Check if Stripe is installed
pip list | grep stripe

# Install if missing
pip install stripe
```

### Import Errors
```bash
# Test individual components
python -c "from server.models.invoice import Invoice; print('OK')"
python -c "from server.services.payment_service import PaymentService; print('OK')"
```

### Configuration Issues
```bash
# Validate environment variables
python -c "
from server.config.payment_config import PaymentConfig
PaymentConfig.validate_config()
"
```

## 📚 Next Steps

1. **Install Stripe**: `pip install stripe`
2. **Get API Keys**: From Stripe Dashboard
3. **Configure Webhooks**: In Stripe Dashboard
4. **Test Integration**: Run test script
5. **Start Server**: Should work without errors

## 🆘 Need Help?

- Check the full [PAYMENT_INTEGRATION_README.md](PAYMENT_INTEGRATION_README.md)
- Run the test script: `python test_payment_integration.py`
- Check server logs for specific error messages
- Verify your `.env` file configuration

---

**The payment system is ready to use once Stripe is configured! 🎉**
