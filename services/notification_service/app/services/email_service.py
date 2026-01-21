"""
Email Service - SendGrid Integration

TODO: Implement SendGrid email sending.
"""

from typing import Optional, Dict, Any
import uuid

from app.schemas.notification import NotificationResponse, NotificationType
from app.config import settings


class EmailService:
    """
    Email service for sending emails via SendGrid.
    
    TODO: Integrate with SendGrid SDK
    TODO: Add email templates
    TODO: Add rate limiting
    """
    
    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.sendgrid_from_email
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        to_name: Optional[str] = None,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
    ) -> NotificationResponse:
        """
        Send an email.
        
        TODO: Integrate with SendGrid
        
        Example with SendGrid:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=self.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=body_html,
        )
        sg = SendGridAPIClient(self.api_key)
        response = sg.send(message)
        """
        
        # Get HTML content
        if template_name:
            body_html = self._render_template(template_name, template_data or {})
        
        # Mock sending email
        notification_id = str(uuid.uuid4())
        
        print(f"[EMAIL] Sending to: {to_email}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body: {body_html[:100] if body_html else body_text[:100]}...")
        
        return NotificationResponse(
            success=True,
            notification_id=notification_id,
            channel="email",
            recipient=to_email,
            message=f"Email sent to {to_email}",
        )
    
    async def send_order_notification(
        self,
        order_id: int,
        order_number: str,
        customer_email: str,
        customer_name: str,
        notification_type: NotificationType,
        order_data: Dict[str, Any],
    ) -> NotificationResponse:
        """Send order-related email notification."""
        
        template_map = {
            NotificationType.ORDER_CONFIRMATION: "order_confirmation",
            NotificationType.ORDER_SHIPPED: "order_shipped",
            NotificationType.ORDER_DELIVERED: "order_delivered",
        }
        
        subject_map = {
            NotificationType.ORDER_CONFIRMATION: f"Order Confirmed - #{order_number}",
            NotificationType.ORDER_SHIPPED: f"Your Order Has Shipped - #{order_number}",
            NotificationType.ORDER_DELIVERED: f"Order Delivered - #{order_number}",
        }
        
        template_name = template_map.get(notification_type, "order_confirmation")
        subject = subject_map.get(notification_type, f"Order Update - #{order_number}")
        
        template_data = {
            "customer_name": customer_name,
            "order_number": order_number,
            "order_id": order_id,
            **order_data,
        }
        
        return await self.send_email(
            to_email=customer_email,
            to_name=customer_name,
            subject=subject,
            template_name=template_name,
            template_data=template_data,
        )
    
    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render email template with data.
        
        TODO: Implement proper template rendering (Jinja2)
        """
        templates = {
            "order_confirmation": f"""
                <h1>Thank you for your order!</h1>
                <p>Hi {data.get('customer_name', 'Customer')},</p>
                <p>Your order #{data.get('order_number', '')} has been confirmed.</p>
                <p>We'll send you another email when your order ships.</p>
            """,
            "order_shipped": f"""
                <h1>Your order is on its way!</h1>
                <p>Hi {data.get('customer_name', 'Customer')},</p>
                <p>Your order #{data.get('order_number', '')} has been shipped.</p>
                <p>Tracking: {data.get('tracking_number', 'N/A')}</p>
            """,
            "order_delivered": f"""
                <h1>Your order has been delivered!</h1>
                <p>Hi {data.get('customer_name', 'Customer')},</p>
                <p>Your order #{data.get('order_number', '')} has been delivered.</p>
            """,
            "password_reset": f"""
                <h1>Password Reset Request</h1>
                <p>Click the link below to reset your password:</p>
                <a href="{data.get('reset_link', '#')}">Reset Password</a>
            """,
            "welcome": f"""
                <h1>Welcome to our store!</h1>
                <p>Hi {data.get('customer_name', 'Customer')},</p>
                <p>Thank you for creating an account with us.</p>
            """,
        }
        
        return templates.get(template_name, f"<p>Notification: {template_name}</p>")
