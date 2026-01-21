"""
Payment Service - Business Logic Layer

TODO: Implement Stripe integration here.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
import json
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentIntentResponse, RefundResponse
from app.config import settings


class PaymentService:
    """
    Payment service for handling payment-related business logic.
    
    TODO: Integrate with Stripe SDK
    TODO: Add PayPal support
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_payment(self, payment_id: int, user_id: Optional[int] = None) -> Optional[Payment]:
        """Get payment by ID."""
        query = select(Payment).where(Payment.id == payment_id)
        if user_id:
            query = query.where(Payment.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_payment_by_order(self, order_id: int, user_id: Optional[int] = None) -> Optional[Payment]:
        """Get payment for an order."""
        query = select(Payment).where(Payment.order_id == order_id)
        if user_id:
            query = query.where(Payment.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_payment_intent(
        self,
        user_id: int,
        payment_data: PaymentCreate,
    ) -> PaymentIntentResponse:
        """
        Create a Stripe payment intent.
        
        TODO: Integrate with Stripe SDK
        For now, returns a mock response.
        """
        # Create payment record
        payment = Payment(
            order_id=payment_data.order_id,
            user_id=user_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            status=PaymentStatus.PENDING,
            payment_method=payment_data.payment_method,
        )
        
        self.db.add(payment)
        await self.db.flush()
        
        # TODO: Create Stripe payment intent
        # import stripe
        # stripe.api_key = settings.stripe_secret_key
        # intent = stripe.PaymentIntent.create(
        #     amount=int(payment_data.amount * 100),  # Stripe uses cents
        #     currency=payment_data.currency.lower(),
        #     metadata={"order_id": payment_data.order_id, "payment_id": payment.id},
        # )
        # payment.stripe_payment_intent_id = intent.id
        
        # Mock response
        mock_intent_id = f"pi_mock_{payment.id}"
        mock_client_secret = f"{mock_intent_id}_secret_mock"
        
        payment.stripe_payment_intent_id = mock_intent_id
        payment.status = PaymentStatus.PROCESSING
        
        await self.db.flush()
        await self.db.refresh(payment)
        
        return PaymentIntentResponse(
            payment_id=payment.id,
            client_secret=mock_client_secret,
            amount=payment.amount,
            currency=payment.currency,
            status="requires_payment_method",
        )
    
    async def confirm_payment(self, payment_id: int, stripe_payment_intent_id: str) -> Payment:
        """
        Confirm payment after successful charge.
        
        Called by webhook handler.
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(payment)
        
        # Notify order service
        await self._notify_order_service(payment.order_id, payment.id, "completed")
        
        return payment
    
    async def fail_payment(self, payment_id: int, error_message: str, error_code: str = None) -> Payment:
        """Mark payment as failed."""
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        payment.status = PaymentStatus.FAILED
        payment.error_message = error_message
        payment.error_code = error_code
        
        await self.db.flush()
        await self.db.refresh(payment)
        
        # Notify order service
        await self._notify_order_service(payment.order_id, payment.id, "failed")
        
        return payment
    
    async def process_refund(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> RefundResponse:
        """
        Process a refund.
        
        TODO: Integrate with Stripe refund API
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError("Can only refund completed payments")
        
        refund_amount = amount or payment.amount
        
        if refund_amount > payment.amount:
            raise ValueError("Refund amount exceeds payment amount")
        
        # TODO: Process refund through Stripe
        # refund = stripe.Refund.create(
        #     payment_intent=payment.stripe_payment_intent_id,
        #     amount=int(refund_amount * 100),
        # )
        
        payment.status = PaymentStatus.REFUNDED
        payment.refund_amount = refund_amount
        payment.refund_reason = reason
        payment.refunded_at = datetime.utcnow()
        
        await self.db.flush()
        
        return RefundResponse(
            payment_id=payment.id,
            refund_amount=refund_amount,
            status="succeeded",
            refunded_at=payment.refunded_at,
        )
    
    async def handle_stripe_webhook(self, payload: bytes, sig_header: str) -> dict:
        """
        Handle Stripe webhook events.
        
        TODO: Verify webhook signature
        TODO: Handle all relevant event types
        """
        try:
            event_data = json.loads(payload)
            event_type = event_data.get("type", "")
            
            # TODO: Verify signature
            # event = stripe.Webhook.construct_event(
            #     payload, sig_header, settings.stripe_webhook_secret
            # )
            
            if event_type == "payment_intent.succeeded":
                intent = event_data.get("data", {}).get("object", {})
                payment_id = intent.get("metadata", {}).get("payment_id")
                if payment_id:
                    await self.confirm_payment(int(payment_id), intent.get("id"))
                return {"status": "payment_confirmed"}
            
            elif event_type == "payment_intent.payment_failed":
                intent = event_data.get("data", {}).get("object", {})
                payment_id = intent.get("metadata", {}).get("payment_id")
                error = intent.get("last_payment_error", {})
                if payment_id:
                    await self.fail_payment(
                        int(payment_id),
                        error.get("message", "Payment failed"),
                        error.get("code"),
                    )
                return {"status": "payment_failed"}
            
            return {"status": "unhandled_event", "type": event_type}
            
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON payload")
    
    async def _notify_order_service(self, order_id: int, payment_id: int, status: str):
        """Notify order service about payment status."""
        try:
            async with httpx.AsyncClient() as client:
                if status == "completed":
                    await client.post(
                        f"{settings.order_service_url}/api/v1/orders/{order_id}/payment-success",
                        json={"payment_id": payment_id},
                    )
                elif status == "failed":
                    await client.post(
                        f"{settings.order_service_url}/api/v1/orders/{order_id}/payment-failed",
                        json={"payment_id": payment_id},
                    )
        except Exception as e:
            print(f"Error notifying order service: {e}")
            # TODO: Implement retry or message queue
