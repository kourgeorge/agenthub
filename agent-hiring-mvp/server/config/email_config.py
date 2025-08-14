"""Email configuration for the application."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class EmailConfig:
    """Configuration for email services."""
    
    # Gmail SMTP Configuration - Read from environment variables
    SMTP_SERVER = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("GMAIL_EMAIL", "")
    SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")  # Default fallback
    
    # Email Templates
    COMPANY_NAME = os.getenv("COMPANY_NAME", "AgentHub")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@agenthub.com")
    
    # Email Subjects
    PASSWORD_RESET_SUBJECT = f"Password Reset Request - {COMPANY_NAME}"
    NEW_PASSWORD_SUBJECT = f"Your New Password - {COMPANY_NAME}"
    VERIFICATION_SUBJECT = f"Verify Your Email - {COMPANY_NAME}"
    WELCOME_SUBJECT = f"Welcome to {COMPANY_NAME}!"
    
    @classmethod
    def get_smtp_config(cls) -> dict:
        """Get SMTP configuration."""
        return {
            'server': cls.SMTP_SERVER,
            'port': cls.SMTP_PORT,
            'email': cls.SENDER_EMAIL,
            'password': cls.SENDER_PASSWORD
        }
    
    @classmethod
    def get_from_email(cls) -> str:
        """Get the sender email address."""
        return cls.SENDER_EMAIL
    
    @classmethod
    def get_company_name(cls) -> str:
        """Get the company name for emails."""
        return cls.COMPANY_NAME
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required email configuration is present."""
        print(f"🔍 Email Configuration Debug:")
        print(f"   SMTP Server: {cls.SMTP_SERVER}")
        print(f"   SMTP Port: {cls.SMTP_PORT}")
        print(f"   Sender Email: {cls.SENDER_EMAIL}")
        print(f"   Sender Password: {'*' * len(cls.SENDER_PASSWORD) if cls.SENDER_PASSWORD else 'NOT SET'}")
        print(f"   Company Name: {cls.COMPANY_NAME}")
        
        required_vars = [
            cls.SENDER_EMAIL,
            cls.SENDER_PASSWORD
        ]
        
        missing_vars = [var for var in required_vars if not var]
        
        if missing_vars:
            print(f"❌ Missing required email configuration: {missing_vars}")
            print("   Please check your .env file")
            return False
        
        print(f"✅ Email configuration validation passed")
        return True
