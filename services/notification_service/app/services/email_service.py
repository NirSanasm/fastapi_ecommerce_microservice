"""
Email Service - Brevo (Sendinblue) Integration
"""

from typing import Optional, Dict, Any
import uuid
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.schemas.notification import NotificationResponse, NotificationType
from app.config import settings


class EmailService:
    """
    Email service for sending emails via Brevo (Sendinblue).
    """
    
    def __init__(self):
        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.brevo_api_key
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        self.from_email = settings.brevo_from_email
        self.from_name = settings.brevo_from_name
    
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
        Send an email via Brevo.
        """
        # Get HTML content
        if template_name:
            body_html = self._render_template(template_name, template_data or {})
        
        notification_id = str(uuid.uuid4())
        
        # Build email
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"email": self.from_email, "name": self.from_name},
            to=[{"email": to_email, "name": to_name or to_email}],
            subject=subject,
            html_content=body_html,
            text_content=body_text,
        )
        
        try:
            # Send email via Brevo API
            response = self.api_instance.send_transac_email(send_smtp_email)
            
            return NotificationResponse(
                success=True,
                notification_id=response.message_id or notification_id,
                channel="email",
                recipient=to_email,
                message=f"Email sent to {to_email}",
            )
        except ApiException as e:
            print(f"[EMAIL ERROR] Brevo API error: {e}")
            return NotificationResponse(
                success=False,
                notification_id=notification_id,
                channel="email",
                recipient=to_email,
                message=f"Failed to send email: {str(e)}",
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
        """Render email template with data."""
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
