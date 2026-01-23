"""
Payments Router - Payment processing endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.database import get_db
from app.config import settings
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentIntentResponse,
    RefundRequest,
    RefundResponse,
)
from app.services.payment_service import PaymentService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel
from shared.auth import verify_token, TokenData


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Extract and validate user from JWT token."""
    try:
        token_data = verify_token(
            credentials.credentials,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
            verify_type="access",
        )
        return token_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def require_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """Require admin role for access."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/create-intent", response_model=ResponseModel[PaymentIntentResponse])
async def create_payment_intent(
    payment_data: PaymentCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a payment intent for an order.
    
    Returns a client secret for frontend to complete payment.
    """
    user_id = int(current_user.user_id)
    payment_service = PaymentService(db)
    
    try:
        intent = await payment_service.create_payment_intent(user_id, payment_data)
        return ResponseModel(
            success=True,
            message="Payment intent created",
            data=intent,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{payment_id}", response_model=ResponseModel[PaymentResponse])
async def get_payment(
    payment_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment details by ID."""
    user_id = int(current_user.user_id)
    payment_service = PaymentService(db)
    
    payment = await payment_service.get_payment(payment_id, user_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    return ResponseModel(success=True, data=payment)


@router.post("/refund", response_model=ResponseModel[RefundResponse])
async def process_refund(
    refund_data: RefundRequest,
    admin_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a refund for a payment.
    
    Requires admin role.
    """
    payment_service = PaymentService(db)
    
    try:
        refund = await payment_service.process_refund(
            refund_data.payment_id,
            refund_data.amount,
            refund_data.reason,
        )
        return ResponseModel(
            success=True,
            message="Refund processed successfully",
            data=refund,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhooks.
    
    TODO: Verify webhook signature
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.handle_stripe_webhook(payload, sig_header)
        return {"received": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/order/{order_id}", response_model=ResponseModel[PaymentResponse])
async def get_payment_by_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment for an order."""
    user_id = int(current_user.user_id)
    payment_service = PaymentService(db)
    
    payment = await payment_service.get_payment_by_order(order_id, user_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    return ResponseModel(success=True, data=payment)


@router.post("/test/confirm/{payment_id}", response_model=ResponseModel[PaymentResponse])
async def confirm_payment_test(
    payment_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    [TEST ONLY] Confirm a payment using Stripe test card.
    
    This endpoint is for development testing only.
    Uses pm_card_visa test payment method.
    """
    if not settings.stripe_secret_key.startswith("sk_test_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint only works in Stripe test mode"
        )
    
    payment_service = PaymentService(db)
    
    try:
        payment = await payment_service.confirm_payment_test(payment_id)
        return ResponseModel(
            success=True,
            message="Payment confirmed (test mode)",
            data=payment,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
