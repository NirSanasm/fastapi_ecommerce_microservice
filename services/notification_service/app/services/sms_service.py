"""
SMS Service - Twilio Integration

TODO: Implement Twilio SMS sending.
"""

import uuid
from app.schemas.notification import NotificationResponse
from app.config import settings


class SMSService:
    """
    SMS service for sending text messages via Twilio.
    
    TODO: Integrate with Twilio SDK
    TODO: Add rate limiting
    """
    
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_phone = settings.twilio_from_phone
    
    async def send_sms(self, to_phone: str, message: str) -> NotificationResponse:
        """
        Send an SMS message.
        
        TODO: Integrate with Twilio
        
        Example with Twilio:
        from twilio.rest import Client
        
        client = Client(self.account_sid, self.auth_token)
        message = client.messages.create(
            body=message,
            from_=self.from_phone,
            to=to_phone,
        )
        """
        
        # Mock sending SMS
        notification_id = str(uuid.uuid4())
        
        print(f"[SMS] Sending to: {to_phone}")
        print(f"[SMS] Message: {message}")
        
        return NotificationResponse(
            success=True,
            notification_id=notification_id,
            channel="sms",
            recipient=to_phone,
            message=f"SMS sent to {to_phone}",
        )
