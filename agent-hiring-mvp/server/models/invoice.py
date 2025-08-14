"""Invoice model for storing billing and payment information."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base

class Invoice(Base):
    """Invoice model for tracking billing and payments."""
    
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    stripe_invoice_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # User and billing information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="draft")  # draft, sent, paid, overdue, cancelled
    
    # Invoice details
    description = Column(Text, nullable=True)
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Payment information
    payment_method_id = Column(String(100), nullable=True)
    payment_intent_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    amount_paid = Column(Float, default=0.0)
    
    # Additional Data
    invoice_data = Column(Text, nullable=True)  # JSON string for additional data
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="invoices")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', amount={self.amount}, status='{self.status}')>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if not self.due_date or self.status == "paid":
            return False
        return datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self) -> int:
        """Get number of days overdue."""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow() - self.due_date).days
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.status == "paid" and self.amount_paid >= self.amount
    
    @property
    def remaining_balance(self) -> float:
        """Get remaining balance to be paid."""
        return max(0, self.amount - self.amount_paid)
    
    def to_dict(self) -> dict:
        """Convert invoice to dictionary."""
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "stripe_invoice_id": self.stripe_invoice_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "description": self.description,
            "billing_period_start": self.billing_period_start.isoformat() if self.billing_period_start else None,
            "billing_period_end": self.billing_period_end.isoformat() if self.billing_period_end else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "payment_method_id": self.payment_method_id,
            "payment_intent_id": self.payment_intent_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "amount_paid": self.amount_paid,
            "invoice_data": self.invoice_data,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_overdue": self.is_overdue,
            "days_overdue": self.days_overdue,
            "is_paid": self.is_paid,
            "remaining_balance": self.remaining_balance
        }
