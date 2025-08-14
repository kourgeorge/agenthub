"""Email service for authentication and notifications."""

import os
from typing import Optional
from datetime import datetime, timedelta
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add the project root to Python path for absolute imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.config.email_config import EmailConfig

class EmailService:
    """Service for sending emails using Gmail SMTP."""
    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure password reset token."""
        # Generate a 32-character random token
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure email verification token."""
        # Generate a 24-character random token
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(24))
    
    @staticmethod
    def generate_random_password() -> str:
        """Generate a secure random password for users."""
        # Generate a 12-character random password with mixed characters
        length = 12
        # Ensure at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*"
        
        # Start with one character from each category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]
        
        # Fill the rest with random characters
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return ''.join(password_list)
    
    @staticmethod
    def _send_email_via_gmail(to_email: str, subject: str, html_content: str) -> bool:
        """Send email via Gmail SMTP."""
        try:
            # Get SMTP configuration
            smtp_config = EmailConfig.get_smtp_config()
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config['email']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect to Gmail SMTP server
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            server.starttls()  # Enable TLS encryption
            
            # Login to Gmail
            server.login(smtp_config['email'], smtp_config['password'])
            
            # Send email
            text = msg.as_string()
            server.sendmail(smtp_config['email'], to_email, text)
            
            # Close connection
            server.quit()
            
            print(f"[EMAIL SERVICE] Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"[EMAIL SERVICE] Failed to send email to {to_email}: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(email: str, reset_token: str, reset_url: str) -> bool:
        """Send password reset email via Gmail."""
        subject = EmailConfig.PASSWORD_RESET_SUBJECT
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset Request - AgentHub</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px 24px; text-align: center;">
                    <div style="display: inline-block; background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                        <span style="font-size: 32px; font-weight: bold; color: #3b82f6;">A</span>
                    </div>
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">AgentHub</h1>
                    <p style="color: #dbeafe; margin: 8px 0 0 0; font-size: 16px;">Your AI Agent Platform</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 24px;">
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="display: inline-block; background-color: #dbeafe; border-radius: 50%; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                            <span style="font-size: 32px; color: #3b82f6;">🔐</span>
                        </div>
                        <h2 style="color: #1e293b; margin: 0 0 8px 0; font-size: 24px; font-weight: 600;">Password Reset Request</h2>
                        <p style="color: #64748b; margin: 0; font-size: 16px;">We received a request to reset your password</p>
                    </div>
                    
                    <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin-bottom: 24px; border-left: 4px solid #3b82f6;">
                        <p style="color: #1e293b; margin: 0 0 16px 0; font-size: 16px; line-height: 1.6;">
                            You have requested a password reset for your AgentHub account. Click the button below to create a new password.
                        </p>
                        <div style="text-align: center;">
                            <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);">
                                Reset My Password
                            </a>
                        </div>
                    </div>
                    
                    <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 20px; margin-right: 8px;">⏰</span>
                            <strong style="color: #92400e; font-size: 16px;">Important Notice</strong>
                        </div>
                        <p style="color: #92400e; margin: 0; font-size: 14px; line-height: 1.5;">
                            This password reset link will expire in 1 hour for security reasons.
                        </p>
                    </div>
                    
                    <div style="background-color: #f1f5f9; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                        <h4 style="color: #1e293b; margin: 0 0 12px 0; font-size: 16px; font-weight: 600;">Security Tips:</h4>
                        <ul style="color: #475569; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Never share your password with anyone</li>
                            <li>Use a strong, unique password</li>
                            <li>Enable two-factor authentication if available</li>
                            <li>Keep your password reset link private</li>
                        </ul>
                    </div>
                    
                    <div style="border-top: 1px solid #e2e8f0; padding-top: 24px; text-align: center;">
                        <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                            If you didn't request this password reset, please ignore this email.
                        </p>
                        <p style="color: #64748b; margin: 0; font-size: 14px;">
                            <strong>Support Email:</strong> support@agenthub.com
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                        © 2024 AgentHub. All rights reserved.
                    </p>
                    <p style="color: #94a3b8; margin: 0; font-size: 12px;">
                        This email was sent to {email}. If you have any questions, please contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email_via_gmail(email, subject, html_content)
    
    @staticmethod
    def send_new_password_email(email: str, new_password: str) -> bool:
        """Send new password email via Gmail."""
        subject = EmailConfig.NEW_PASSWORD_SUBJECT
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset Complete - AgentHub</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px 24px; text-align: center;">
                    <div style="display: inline-block; background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                        <span style="font-size: 32px; font-weight: bold; color: #3b82f6;">A</span>
                    </div>
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">AgentHub</h1>
                    <p style="color: #dbeafe; margin: 8px 0 0 0; font-size: 16px;">Your AI Agent Platform</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 24px;">
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="display: inline-block; background-color: #dcfce7; border-radius: 50%; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                            <span style="font-size: 32px; color: #16a34a;">✓</span>
                        </div>
                        <h2 style="color: #1e293b; margin: 0 0 8px 0; font-size: 24px; font-weight: 600;">Password Reset Complete</h2>
                        <p style="color: #64748b; margin: 0; font-size: 16px;">Your password has been successfully reset</p>
                    </div>
                    
                    <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin-bottom: 24px; border-left: 4px solid #3b82f6;">
                        <h3 style="color: #1e293b; margin: 0 0 16px 0; font-size: 18px; font-weight: 600;">Your New Password</h3>
                        <div style="background-color: #ffffff; border: 2px solid #e2e8f0; border-radius: 6px; padding: 16px; text-align: center; font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #1e293b; letter-spacing: 1px;">
                            {new_password}
                        </div>
                        <p style="color: #64748b; margin: 16px 0 0 0; font-size: 14px; text-align: center;">Copy this password carefully</p>
                    </div>
                    
                    <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 20px; margin-right: 8px;">⚠️</span>
                            <strong style="color: #92400e; font-size: 16px;">Security Notice</strong>
                        </div>
                        <p style="color: #92400e; margin: 0; font-size: 14px; line-height: 1.5;">
                            For your security, please change this password immediately after logging into your AgentHub account.
                        </p>
                    </div>
                    
                    <div style="background-color: #f1f5f9; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                        <h4 style="color: #1e293b; margin: 0 0 12px 0; font-size: 16px; font-weight: 600;">Next Steps:</h4>
                        <ol style="color: #475569; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Sign in to your AgentHub account using the new password above</li>
                            <li>Go to your Profile settings</li>
                            <li>Change your password to something you'll remember</li>
                            <li>Consider enabling two-factor authentication for extra security</li>
                        </ol>
                    </div>
                    
                    <div style="text-align: center; margin-bottom: 24px;">
                        <a href="#" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);">
                            Sign In to AgentHub
                        </a>
                    </div>
                    
                    <div style="border-top: 1px solid #e2e8f0; padding-top: 24px; text-align: center;">
                        <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                            If you didn't request this password reset, please contact our support team immediately.
                        </p>
                        <p style="color: #64748b; margin: 0; font-size: 14px;">
                            <strong>Support Email:</strong> support@agenthub.com
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                        © 2024 AgentHub. All rights reserved.
                    </p>
                    <p style="color: #94a3b8; margin: 0; font-size: 12px;">
                        This email was sent to {email}. If you have any questions, please contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email_via_gmail(email, subject, html_content)
    
    @staticmethod
    def send_verification_email(email: str, verification_token: str, verification_url: str) -> bool:
        """Send email verification email via Gmail."""
        subject = EmailConfig.VERIFICATION_SUBJECT
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email - AgentHub</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px 24px; text-align: center;">
                    <div style="display: inline-block; background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                        <span style="font-size: 32px; font-weight: bold; color: #3b82f6;">A</span>
                    </div>
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">AgentHub</h1>
                    <p style="color: #dbeafe; margin: 8px 0 0 0; font-size: 16px;">Your AI Agent Platform</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 24px;">
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="display: inline-block; background-color: #dbeafe; border-radius: 50%; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                            <span style="font-size: 32px; color: #3b82f6;">✉️</span>
                        </div>
                        <h2 style="color: #1e293b; margin: 0 0 8px 0; font-size: 24px; font-weight: 600;">Verify Your Email Address</h2>
                        <p style="color: #64748b; margin: 0; font-size: 16px;">One more step to complete your registration</p>
                    </div>
                    
                    <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin-bottom: 24px; border-left: 4px solid #3b82f6;">
                        <p style="color: #1e293b; margin: 0 0 16px 0; font-size: 16px; line-height: 1.6;">
                            Welcome to AgentHub! To complete your registration and start using our platform, please verify your email address by clicking the button below.
                        </p>
                        <div style="text-align: center;">
                            <a href="{verification_url}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);">
                                Verify My Email
                            </a>
                        </div>
                    </div>
                    
                    <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 20px; margin-right: 8px;">🔒</span>
                            <strong style="color: #92400e; font-size: 16px;">Security Notice</strong>
                        </div>
                        <p style="color: #92400e; margin: 0; font-size: 14px; line-height: 1.5;">
                            This verification link is unique to your account and should not be shared with anyone.
                        </p>
                    </div>
                    
                    <div style="background-color: #f1f5f9; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                        <h4 style="color: #1e293b; margin: 0 0 12px 0; font-size: 16px; font-weight: 600;">What happens next:</h4>
                        <ol style="color: #475569; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Click the verification button above</li>
                            <li>Your email will be verified instantly</li>
                            <li>You'll be redirected to your AgentHub dashboard</li>
                            <li>Start exploring AI agents and building your own!</li>
                        </ol>
                    </div>
                    
                    <div style="border-top: 1px solid #e2e8f0; padding-top: 24px; text-align: center;">
                        <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                            If you didn't create an account, please ignore this email.
                        </p>
                        <p style="color: #64748b; margin: 0; font-size: 14px;">
                            <strong>Support Email:</strong> support@agenthub.com
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                        © 2024 AgentHub. All rights reserved.
                    </p>
                    <p style="color: #94a3b8; margin: 0; font-size: 12px;">
                        This email was sent to {email}. We're excited to have you join the AgentHub community!
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email_via_gmail(email, subject, html_content)
    
    @staticmethod
    def send_welcome_email(email: str, username: str) -> bool:
        """Send welcome email to new users via Gmail."""
        subject = EmailConfig.WELCOME_SUBJECT
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to AgentHub!</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px 24px; text-align: center;">
                    <div style="display: inline-block; background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                        <span style="font-size: 32px; font-weight: bold; color: #3b82f6;">A</span>
                    </div>
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">AgentHub</h1>
                    <p style="color: #dbeafe; margin: 8px 0 0 0; font-size: 16px;">Your AI Agent Platform</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 24px;">
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="display: inline-block; background-color: #dcfce7; border-radius: 50%; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                            <span style="font-size: 32px; color: #16a34a;">🎉</span>
                        </div>
                        <h2 style="color: #1e293b; margin: 0 0 8px 0; font-size: 24px; font-weight: 600;">Welcome to AgentHub, {username}!</h2>
                        <p style="color: #64748b; margin: 0; font-size: 16px;">Your account has been created successfully</p>
                    </div>
                    
                    <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin-bottom: 24px; border-left: 4px solid #3b82f6;">
                        <p style="color: #1e293b; margin: 0 0 16px 0; font-size: 16px; line-height: 1.6;">
                            Thank you for joining AgentHub! We're excited to have you on board. Your account is now ready and you can start exploring the world of AI agents.
                        </p>
                    </div>
                    
                    <div style="background-color: #f1f5f9; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                        <h4 style="color: #1e293b; margin: 0 0 16px 0; font-size: 16px; font-weight: 600;">What you can do now:</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                            <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <div style="text-align: center; margin-bottom: 8px;">
                                    <span style="font-size: 24px;">🤖</span>
                                </div>
                                <h5 style="color: #1e293b; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Browse & Hire Agents</h5>
                                <p style="color: #64748b; margin: 0; font-size: 12px; line-height: 1.4;">Discover AI agents for your specific needs</p>
                            </div>
                            <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <div style="text-align: center; margin-bottom: 8px;">
                                    <span style="font-size: 24px;">⚡</span>
                                </div>
                                <h5 style="color: #1e293b; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Create Agents</h5>
                                <p style="color: #64748b; margin: 0; font-size: 12px; line-height: 1.4;">Build and deploy your own AI agents</p>
                            </div>
                            <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <div style="text-align: center; margin-bottom: 8px;">
                                    <span style="font-size: 24px;">📊</span>
                                </div>
                                <h5 style="color: #1e293b; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Manage Deployments</h5>
                                <p style="color: #64748b; margin: 0; font-size: 12px; line-height: 1.4;">Monitor and control your agent deployments</p>
                            </div>
                            <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <div style="text-align: center; margin-bottom: 8px;">
                                    <span style="font-size: 24px;">💰</span>
                                </div>
                                <h5 style="color: #1e293b; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Track Usage & Billing</h5>
                                <p style="color: #64748b; margin: 0; font-size: 12px; line-height: 1.4;">Monitor costs and resource usage</p>
                            </div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-bottom: 24px;">
                        <a href="#" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);">
                            Get Started with AgentHub
                        </a>
                    </div>
                    
                    <div style="border-top: 1px solid #e2e8f0; padding-top: 24px; text-align: center;">
                        <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                            If you have any questions, feel free to contact our support team.
                        </p>
                        <p style="color: #64748b; margin: 0; font-size: 14px;">
                            <strong>Support Email:</strong> support@agenthub.com
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">
                        © 2024 AgentHub. All rights reserved.
                    </p>
                    <p style="color: #94a3b8; margin: 0; font-size: 12px;">
                        This email was sent to {email}. Welcome to the AgentHub community!
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService._send_email_via_gmail(email, subject, html_content)
