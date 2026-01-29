"""
Payment Service - Business Logic Layer

Integrates with Stripe for payment processing.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
import json
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentIntentResponse, RefundResponse
from app.config import settings
from app.events import event_publisher

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


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
        
        Creates a PaymentIntent on Stripe and stores the payment record locally.
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
        
        try:
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment_data.amount * 100),  # Stripe uses cents
                currency=payment_data.currency.lower(),
                metadata={
                    "order_id": str(payment_data.order_id),
                    "payment_id": str(payment.id),
                },
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never",
                },
            )
            
            payment.stripe_payment_intent_id = intent.id
            payment.status = PaymentStatus.PROCESSING
            
            await self.db.flush()
            await self.db.refresh(payment)
            
            return PaymentIntentResponse(
                payment_id=payment.id,
                client_secret=intent.client_secret,
                amount=payment.amount,
                currency=payment.currency,
                status=intent.status,
            )
        except stripe.error.StripeError as e:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            await self.db.flush()
            raise ValueError(f"Stripe error: {str(e)}")
    
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
        
        # Publish payment.completed event
        await event_publisher.publish_payment_completed(
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            amount=payment.amount,
            stripe_payment_id=stripe_payment_intent_id,
        )
        
        return payment
    
    async def confirm_payment_test(self, payment_id: int) -> Payment:
        """
        [TEST ONLY] Confirm payment using Stripe test card.
        
        Uses pm_card_visa test payment method to simulate card payment.
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if not payment.stripe_payment_intent_id:
            raise ValueError("No Stripe payment intent found")
        
        try:
            # Confirm the payment intent with test card
            stripe.PaymentIntent.confirm(
                payment.stripe_payment_intent_id,
                payment_method="pm_card_visa",
            )
            
            # Update local payment status
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            
            await self.db.flush()
            await self.db.refresh(payment)
            
            return payment
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe error: {str(e)}")
    
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
        
        # Publish payment.failed event
        await event_publisher.publish_payment_failed(
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            error_message=error_message,
        )
        
        return payment
    
    async def process_refund(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> RefundResponse:
        """
        Process a refund via Stripe.
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError("Can only refund completed payments")
        
        refund_amount = amount or payment.amount
        
        if refund_amount > payment.amount:
            raise ValueError("Refund amount exceeds payment amount")
        
        try:
            # Process refund through Stripe
            refund_params = {
                "payment_intent": payment.stripe_payment_intent_id,
            }
            # Only specify amount for partial refunds
            if amount and amount < payment.amount:
                refund_params["amount"] = int(refund_amount * 100)
            if reason:
                refund_params["reason"] = "requested_by_customer"
            
            stripe.Refund.create(**refund_params)
            
            payment.status = PaymentStatus.REFUNDED
            payment.refund_amount = refund_amount
            payment.refund_reason = reason
            payment.refunded_at = datetime.utcnow()
            
            await self.db.flush()
            
            # Publish payment.refunded event
            await event_publisher.publish_payment_refunded(
                payment_id=payment.id,
                order_id=payment.order_id,
                user_id=payment.user_id,
                amount=refund_amount,
            )
            
            return RefundResponse(
                payment_id=payment.id,
                refund_amount=refund_amount,
                status="succeeded",
                refunded_at=payment.refunded_at,
            )
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe refund error: {str(e)}")
    
    async def handle_stripe_webhook(self, payload: bytes, sig_header: str) -> dict:
        """
        Handle Stripe webhook events with signature verification.
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            event_type = event["type"]
            
            if event_type == "payment_intent.succeeded":
                intent = event["data"]["object"]
                payment_id = intent.get("metadata", {}).get("payment_id")
                if payment_id:
                    await self.confirm_payment(int(payment_id), intent["id"])
                return {"status": "payment_confirmed"}
            
            elif event_type == "payment_intent.payment_failed":
                intent = event["data"]["object"]
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
            
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON payload")
