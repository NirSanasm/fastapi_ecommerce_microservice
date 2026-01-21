"""
Notifications Router - Notification sending endpoints
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.notification import (
    EmailNotification,
    SMSNotification,
    NotificationResponse,
    OrderNotification,
)
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel


router = APIRouter()


@router.post("/email", response_model=ResponseModel[NotificationResponse])
async def send_email(notification: EmailNotification):
    """
    Send an email notification.
    
    Supports both template-based and custom HTML emails.
    """
    email_service = EmailService()
    
    try:
        result = await email_service.send_email(
            to_email=notification.to_email,
            to_name=notification.to_name,
            subject=notification.subject,
            template_name=notification.template_name,
            template_data=notification.template_data,
            body_html=notification.body_html,
            body_text=notification.body_text,
        )
        return ResponseModel(
            success=True,
            message="Email sent successfully",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}",
        )


@router.post("/sms", response_model=ResponseModel[NotificationResponse])
async def send_sms(notification: SMSNotification):
    """
    Send an SMS notification.
    """
    sms_service = SMSService()
    
    try:
        result = await sms_service.send_sms(
            to_phone=notification.to_phone,
            message=notification.message,
        )
        return ResponseModel(
            success=True,
            message="SMS sent successfully",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SMS: {str(e)}",
        )


@router.post("/order", response_model=ResponseModel[NotificationResponse])
async def send_order_notification(notification: OrderNotification):
    """
    Send order-related notification (email and optionally SMS).
    
    Automatically selects the appropriate template based on notification type.
    """
    email_service = EmailService()
    
    try:
        result = await email_service.send_order_notification(
            order_id=notification.order_id,
            order_number=notification.order_number,
            customer_email=notification.customer_email,
            customer_name=notification.customer_name,
            notification_type=notification.notification_type,
            order_data=notification.order_data,
        )
        return ResponseModel(
            success=True,
            message=f"{notification.notification_type.value} notification sent",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.get("/templates")
async def list_templates():
    """List available email templates."""
    return ResponseModel(
        success=True,
        data={
            "templates": [
                "order_confirmation",
                "order_shipped",
                "order_delivered",
                "password_reset",
                "welcome",
            ]
        },
    )
