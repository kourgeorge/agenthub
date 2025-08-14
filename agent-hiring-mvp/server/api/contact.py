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
        <html>
        <body>
            <h2>New Contact Form Submission - {company_name}</h2>
            <p><strong>Name:</strong> {contact_data.name}</p>
            <p><strong>Email:</strong> {contact_data.email}</p>
            <p><strong>Subject:</strong> {contact_data.subject}</p>
            <p><strong>Inquiry Type:</strong> {contact_data.inquiry_type}</p>
            <p><strong>Message:</strong></p>
            <p>{contact_data.message}</p>
            <hr>
            <p><em>This message was sent from the {company_name} contact form.</em></p>
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
