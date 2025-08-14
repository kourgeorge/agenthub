"""Contact form API endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from server.services.email_service import EmailService
from server.config.email_config import EmailConfig

router = APIRouter(prefix="/contact", tags=["contact"])

class ContactFormRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    inquiry_type: Optional[str] = "general"

class ContactFormResponse(BaseModel):
    message: str
    success: bool

@router.post("/submit", response_model=ContactFormResponse)
async def submit_contact_form(contact_data: ContactFormRequest):
    """Submit a contact form and send email notification."""
    try:
        # Get configuration from EmailConfig
        company_name = EmailConfig.get_company_name()
        support_email = EmailConfig.get_smtp_config()['email']  # Use the configured sender email
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Contact Form Submission</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f8fafc;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
                    padding: 30px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    display: inline-flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 20px;
                }}
                .logo-icon {{
                    width: 40px;
                    height: 40px;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 20px;
                }}
                .logo-text {{
                    font-size: 24px;
                    font-weight: bold;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .form-section {{
                    background-color: #f8fafc;
                    border-radius: 8px;
                    padding: 25px;
                    margin-bottom: 25px;
                }}
                .form-section h2 {{
                    color: #1e40af;
                    margin-top: 0;
                    margin-bottom: 20px;
                    font-size: 20px;
                    font-weight: 600;
                }}
                .field {{
                    margin-bottom: 15px;
                }}
                .field-label {{
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 5px;
                    display: block;
                }}
                .field-value {{
                    background-color: white;
                    padding: 12px 16px;
                    border-radius: 6px;
                    border: 1px solid #e5e7eb;
                    color: #111827;
                }}
                .message-field {{
                    background-color: white;
                    padding: 16px;
                    border-radius: 6px;
                    border: 1px solid #e5e7eb;
                    color: #111827;
                    white-space: pre-wrap;
                    line-height: 1.5;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 25px 30px;
                    text-align: center;
                    border-top: 1px solid #e5e7eb;
                }}
                .footer p {{
                    margin: 0;
                    color: #6b7280;
                    font-size: 14px;
                }}
                .badge {{
                    display: inline-block;
                    background-color: #3b82f6;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                    margin-left: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">
                        <div class="logo-icon">A</div>
                        <div class="logo-text">AgentHub</div>
                    </div>
                    <h1>New Contact Form Submission</h1>
                    <span class="badge">Contact Form</span>
                </div>
                
                <div class="content">
                    <div class="form-section">
                        <h2>📋 Contact Information</h2>
                        <div class="field">
                            <span class="field-label">👤 Name:</span>
                            <div class="field-value">{contact_data.name}</div>
                        </div>
                        <div class="field">
                            <span class="field-label">📧 Email:</span>
                            <div class="field-value">{contact_data.email}</div>
                        </div>
                        <div class="field">
                            <span class="field-label">📝 Subject:</span>
                            <div class="field-value">{contact_data.subject}</div>
                        </div>
                        <div class="field">
                            <span class="field-label">🏷️ Inquiry Type:</span>
                            <div class="field-value">{contact_data.inquiry_type.title()}</div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <h2>💬 Message</h2>
                        <div class="message-field">{contact_data.message}</div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This message was sent from the {company_name} contact form.</p>
                    <p>Please respond to the user at: <strong>{contact_data.email}</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email to the configured sender email (which will receive contact form submissions)
        email_sent = EmailService._send_email_via_gmail(
            to_email=support_email,
            subject=f"{company_name} Contact Form: {contact_data.subject}",
            html_content=html_content
        )
        
        if email_sent:
            return ContactFormResponse(
                message="Thank you for your message! We'll get back to you within 24 hours.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Please try again later."
            )
            
    except Exception as e:
        print(f"[CONTACT API] Error processing contact form: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again later."
        )
