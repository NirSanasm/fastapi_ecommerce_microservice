"""
Payment Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus, PaymentMethod


class PaymentCreate(BaseModel):
    """Schema for creating a payment/payment intent."""
    order_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    payment_method: PaymentMethod = PaymentMethod.STRIPE


class PaymentIntentResponse(BaseModel):
    """Response with Stripe payment intent details."""
    payment_id: int
    client_secret: str
    amount: Decimal
    currency: str
    status: str


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: int
    order_id: int
    user_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    stripe_payment_intent_id: Optional[str] = None
    error_message: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RefundRequest(BaseModel):
    """Schema for refund request."""
    payment_id: int
    amount: Optional[Decimal] = None  # Full refund if not specified
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    """Schema for refund response."""
    payment_id: int
    refund_amount: Decimal
    status: str
    refunded_at: datetime


class WebhookPayload(BaseModel):
    """Generic webhook payload."""
    type: str
    data: dict
