"""Payment configuration for the application."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class PaymentConfig:
    """Configuration for payment services."""
    
    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Payment Settings
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "usd")
    INVOICE_DUE_DAYS = int(os.getenv("INVOICE_DUE_DAYS", "30"))
    
    # Company Information for Invoices
    COMPANY_NAME = os.getenv("COMPANY_NAME", "AgentHub")
    COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "billing@agenthub.com")
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "")
    
    # Invoice Settings
    INVOICE_PREFIX = os.getenv("INVOICE_PREFIX", "AH")
    AUTO_SEND_INVOICES = os.getenv("AUTO_SEND_INVOICES", "true").lower() == "true"
    
    @classmethod
    def get_stripe_config(cls) -> dict:
        """Get Stripe configuration."""
        return {
            'secret_key': cls.STRIPE_SECRET_KEY,
            'publishable_key': cls.STRIPE_PUBLISHABLE_KEY,
            'webhook_secret': cls.STRIPE_WEBHOOK_SECRET
        }
    
    @classmethod
    def get_company_info(cls) -> dict:
        """Get company information for invoices."""
        return {
            'name': cls.COMPANY_NAME,
            'address': cls.COMPANY_ADDRESS,
            'email': cls.COMPANY_EMAIL,
            'phone': cls.COMPANY_PHONE
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required payment configuration is present."""
        print(f"🔍 Payment Configuration Debug:")
        print(f"   Stripe Secret Key: {'*' * 20 if cls.STRIPE_SECRET_KEY else 'NOT SET'}")
        print(f"   Stripe Publishable Key: {'*' * 20 if cls.STRIPE_PUBLISHABLE_KEY else 'NOT SET'}")
        print(f"   Stripe Webhook Secret: {'*' * 20 if cls.STRIPE_WEBHOOK_SECRET else 'NOT SET'}")
        print(f"   Default Currency: {cls.DEFAULT_CURRENCY}")
        print(f"   Invoice Due Days: {cls.INVOICE_DUE_DAYS}")
        print(f"   Company Name: {cls.COMPANY_NAME}")
        print(f"   Company Email: {cls.COMPANY_EMAIL}")
        
        required_vars = [
            cls.STRIPE_SECRET_KEY,
            cls.STRIPE_PUBLISHABLE_KEY
        ]
        
        missing_vars = [var for var in required_vars if not var]
        
        if missing_vars:
            print(f"❌ Missing required payment configuration: {missing_vars}")
            print("   Please check your .env file")
            return False
        
        print(f"✅ Payment configuration validation passed")
        return True
    
    @classmethod
    def is_test_mode(cls) -> bool:
        """Check if we're in Stripe test mode."""
        return cls.STRIPE_SECRET_KEY.startswith('sk_test_')
    
    @classmethod
    def get_webhook_endpoint(cls) -> str:
        """Get the webhook endpoint URL."""
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        return f"{base_url}/api/v1/webhooks/stripe"
