"""
Notification Pydantic Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class NotificationType(str, Enum):
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    CUSTOM = "custom"


class EmailNotification(BaseModel):
    """Schema for sending email notification."""
    to_email: EmailStr
    to_name: Optional[str] = None
    subject: str
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None


class SMSNotification(BaseModel):
    """Schema for sending SMS notification."""
    to_phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    message: str = Field(..., max_length=160)


class NotificationResponse(BaseModel):
    """Response after sending notification."""
    success: bool
    notification_id: Optional[str] = None
    channel: str  # "email" or "sms"
    recipient: str
    message: str


class BulkEmailRequest(BaseModel):
    """Schema for bulk email sending."""
    recipients: List[EmailStr]
    subject: str
    template_name: str
    template_data: Optional[Dict[str, Any]] = None


class OrderNotification(BaseModel):
    """Schema for order-related notifications."""
    order_id: int
    order_number: str
    customer_email: EmailStr
    customer_name: str
    notification_type: NotificationType
    order_data: Dict[str, Any]
