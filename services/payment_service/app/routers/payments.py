"""
Payments Router - Payment processing endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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


router = APIRouter()


def get_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Extract user ID from authorization header."""
    if authorization:
        return 123  # TODO: Implement JWT validation
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


@router.post("/create-intent", response_model=ResponseModel[PaymentIntentResponse])
async def create_payment_intent(
    payment_data: PaymentCreate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a payment intent for an order.
    
    Returns a client secret for frontend to complete payment.
    """
    user_id = get_user_id(authorization)
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
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get payment details by ID."""
    user_id = get_user_id(authorization)
    payment_service = PaymentService(db)
    
    payment = await payment_service.get_payment(payment_id, user_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    return ResponseModel(success=True, data=payment)


@router.post("/refund", response_model=ResponseModel[RefundResponse])
async def process_refund(
    refund_data: RefundRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a refund for a payment.
    
    TODO: Add admin authentication
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
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get payment for an order."""
    user_id = get_user_id(authorization)
    payment_service = PaymentService(db)
    
    payment = await payment_service.get_payment_by_order(order_id, user_id)
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    return ResponseModel(success=True, data=payment)
