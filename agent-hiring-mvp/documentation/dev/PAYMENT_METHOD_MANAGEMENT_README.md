# Payment Method Management

This document describes the new payment method management feature in AgentHub, which allows customers to securely manage their credit cards and payment methods.

## 🚀 Features

### ✅ What's Implemented
- **Add Payment Methods**: Securely add new credit cards
- **View Payment Methods**: See all saved payment methods
- **Set Default**: Choose which payment method to use by default
- **Delete Payment Methods**: Remove old or unused cards
- **Real-time Validation**: Form validation with helpful error messages
- **Security**: PCI-compliant through Stripe integration
- **Responsive UI**: Works on desktop and mobile devices

### 🔒 Security Features
- **No Local Storage**: Credit card data never touches AgentHub servers
- **Stripe Integration**: All payment processing handled by Stripe
- **PCI Compliance**: Stripe handles all compliance requirements
- **Encrypted Communication**: All API calls use HTTPS

## 🛠️ Technical Implementation

### Frontend Components
- **PaymentMethodManager**: Main React component for managing payment methods
- **Integrated into Billing Page**: Added as a new tab in the billing interface
- **Form Validation**: Client-side validation with real-time feedback
- **Error Handling**: Comprehensive error handling and user feedback

### Backend API Endpoints
```http
GET    /api/v1/billing/payment-methods?user_id={user_id}
POST   /api/v1/billing/payment-methods?user_id={user_id}
POST   /api/v1/billing/payment-methods/{id}/default?user_id={user_id}
DELETE /api/v1/billing/payment-methods/{id}?user_id={user_id}
```

### Database Integration
- **User Model**: Links users to Stripe customers
- **Payment Method Tracking**: Stores payment method metadata (not card details)
- **Invoice Integration**: Links invoices to payment methods

## 📱 User Interface

### Payment Methods Tab
The payment methods management is integrated into the billing page as a new tab:

1. **Navigate to Billing**: Go to `/billing` in the application
2. **Select Payment Methods Tab**: Click on the "Payment Methods" tab
3. **Manage Cards**: Add, view, edit, and delete payment methods

### Add New Payment Method
1. Click "Add Payment Method" button
2. Fill in card details:
   - Card number (auto-formatted)
   - Expiration month/year
   - CVC
   - Name on card
   - Billing ZIP code
3. Click "Add Card" to save

### Manage Existing Methods
- **View Details**: See card brand, last 4 digits, expiration, and status
- **Set Default**: Click "Set Default" to make a card the primary payment method
- **Delete**: Remove cards with confirmation dialog
- **Status Indicators**: Visual indicators for expired, expiring, and valid cards

## 🔧 Setup Requirements

### 1. Stripe Configuration
Ensure these environment variables are set in your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 2. Dependencies
Install the required Python packages:

```bash
pip install stripe
```

### 3. Frontend Dependencies
The frontend uses existing UI components from the design system:
- Button, Card, Input, Label components
- AlertDialog for confirmations
- Badge for status indicators

## 🧪 Testing

### Test the API Endpoints
Run the test script to verify all endpoints work:

```bash
cd agent-hiring-mvp
python test_payment_methods.py
```

### Test with Stripe Test Cards
Use these test card numbers for development:

- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Requires Authentication**: `4000 0025 0000 3155`

### Test Scenarios
1. **Add Payment Method**: Test form validation and submission
2. **View Payment Methods**: Verify empty state and populated lists
3. **Set Default**: Test changing default payment method
4. **Delete Method**: Test removal with confirmation
5. **Error Handling**: Test invalid card numbers, expired dates, etc.

## 📊 API Reference

### Get Payment Methods
```http
GET /api/v1/billing/payment-methods?user_id={user_id}
```

**Response:**
```json
{
  "user_id": 123,
  "payment_methods": [
    {
      "id": "pm_1234567890",
      "type": "card",
      "card": {
        "brand": "visa",
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2025
      },
      "is_default": true,
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### Add Payment Method
```http
POST /api/v1/billing/payment-methods?user_id={user_id}
Content-Type: application/json

{
  "type": "card",
  "card": {
    "number": "4242424242424242",
    "exp_month": 12,
    "exp_year": 2025,
    "cvc": "123"
  },
  "billing_details": {
    "name": "John Doe",
    "address": {
      "postal_code": "12345"
    }
  }
}
```

### Set Default Payment Method
```http
POST /api/v1/billing/payment-methods/{payment_method_id}/default?user_id={user_id}
```

### Delete Payment Method
```http
DELETE /api/v1/billing/payment-methods/{payment_method_id}?user_id={user_id}
```

## 🚨 Error Handling

### Common Error Scenarios
1. **Stripe Not Configured**: Returns 503 Service Unavailable
2. **Invalid Card Data**: Returns 400 Bad Request with validation errors
3. **User Not Found**: Returns 404 Not Found
4. **Payment Method Not Found**: Returns 404 Not Found
5. **Stripe API Errors**: Returns 500 Internal Server Error

### Frontend Error Display
- **Validation Errors**: Real-time form validation with inline messages
- **API Errors**: Toast notifications for server errors
- **Network Errors**: User-friendly error messages for connection issues

## 🔄 Integration Points

### With Existing Systems
- **Billing System**: Payment methods are used for invoice payments
- **User Management**: Links payment methods to user accounts
- **Invoice Generation**: Automatically uses default payment method
- **Webhook Processing**: Stripe webhooks update payment status

### Future Enhancements
- **Recurring Billing**: Automatic payments using saved methods
- **Multiple Currencies**: Support for different payment currencies
- **Payment Analytics**: Track payment method usage patterns
- **Fraud Detection**: Integration with Stripe's fraud prevention

## 📈 Monitoring & Analytics

### Stripe Dashboard
- Monitor payment method creation/deletion
- Track payment success rates
- View customer payment patterns
- Set up alerts for failures

### Application Logs
- Payment method operations logged
- Error tracking and debugging
- User activity monitoring
- Security event logging

## 🛡️ Security Best Practices

### Data Protection
- Never log credit card numbers
- Use HTTPS for all communications
- Implement rate limiting on API endpoints
- Validate all input data

### Access Control
- User authentication required for all operations
- Users can only access their own payment methods
- Admin endpoints protected with proper authorization
- Audit logging for all operations

## 🚀 Deployment

### Production Checklist
- [ ] Stripe live keys configured
- [ ] HTTPS enabled
- [ ] Webhook endpoints configured
- [ ] Error monitoring set up
- [ ] Performance monitoring enabled
- [ ] Security headers configured

### Environment Variables
```bash
# Production
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key
STRIPE_WEBHOOK_SECRET=whsec_your_live_webhook_secret

# Development
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_key
STRIPE_WEBHOOK_SECRET=whsec_your_test_webhook_secret
```

## 📞 Support

### Troubleshooting
1. Check Stripe dashboard for payment method status
2. Verify environment variables are set correctly
3. Check application logs for error details
4. Test with Stripe test cards first

### Getting Help
- Check Stripe documentation for API issues
- Review application logs for debugging
- Test endpoints with the provided test script
- Contact development team for application issues

---

**Note**: This feature requires a valid Stripe account and proper configuration. Test thoroughly in development before deploying to production.
