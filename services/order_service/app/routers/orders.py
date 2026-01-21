"""
Orders Router - Order management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
    OrderStatusUpdate,
    TrackingUpdate,
)
from app.services.order_service import OrderService
from app.models.order import OrderStatus

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel, PaginationParams


router = APIRouter()


def get_user_id(authorization: Optional[str] = Header(None)) -> int:
    """
    Extract user ID from authorization header.
    
    TODO: Implement proper JWT validation
    """
    if authorization:
        # TODO: Decode JWT and extract user ID
        return 123  # Placeholder
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


@router.post("/", response_model=ResponseModel[OrderResponse], status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order from cart.
    
    - Uses items from cart if items not provided
    - Validates stock availability
    - Creates payment intent
    """
    user_id = get_user_id(authorization)
    order_service = OrderService(db)
    
    try:
        order = await order_service.create_order(user_id, order_data)
        return ResponseModel(
            success=True,
            message="Order created successfully",
            data=order,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ResponseModel[List[OrderListResponse]])
async def list_orders(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[OrderStatus] = None,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's orders with optional filtering.
    """
    user_id = get_user_id(authorization)
    order_service = OrderService(db)
    
    orders = await order_service.get_user_orders(
        user_id=user_id,
        skip=pagination.skip,
        limit=pagination.limit,
        status=status_filter,
    )
    
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(orders)} orders",
        data=orders,
    )


@router.get("/{order_id}", response_model=ResponseModel[OrderResponse])
async def get_order(
    order_id: int,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order details by ID.
    """
    user_id = get_user_id(authorization)
    order_service = OrderService(db)
    
    order = await order_service.get_order(order_id, user_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    return ResponseModel(success=True, data=order)


@router.get("/number/{order_number}", response_model=ResponseModel[OrderResponse])
async def get_order_by_number(
    order_number: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order details by order number.
    """
    user_id = get_user_id(authorization)
    order_service = OrderService(db)
    
    order = await order_service.get_by_order_number(order_number, user_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    return ResponseModel(success=True, data=order)


@router.post("/{order_id}/cancel", response_model=ResponseModel[OrderResponse])
async def cancel_order(
    order_id: int,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an order (only if pending/confirmed).
    """
    user_id = get_user_id(authorization)
    order_service = OrderService(db)
    
    try:
        order = await order_service.cancel_order(order_id, user_id)
        return ResponseModel(
            success=True,
            message="Order cancelled successfully",
            data=order,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Admin endpoints

@router.put("/{order_id}/status", response_model=ResponseModel[OrderResponse])
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update order status (admin only).
    
    TODO: Add admin authentication
    """
    order_service = OrderService(db)
    
    order = await order_service.update_status(order_id, status_data.status)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    return ResponseModel(
        success=True,
        message=f"Order status updated to {status_data.status.value}",
        data=order,
    )


@router.put("/{order_id}/tracking", response_model=ResponseModel[OrderResponse])
async def add_tracking(
    order_id: int,
    tracking_data: TrackingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add tracking information to order (admin only).
    
    TODO: Add admin authentication
    """
    order_service = OrderService(db)
    
    order = await order_service.add_tracking(
        order_id,
        tracking_data.tracking_number,
        tracking_data.carrier,
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    return ResponseModel(
        success=True,
        message="Tracking information added",
        data=order,
    )


@router.get("/admin/all", response_model=ResponseModel[List[OrderListResponse]])
async def list_all_orders(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all orders (admin only).
    
    TODO: Add admin authentication
    """
    order_service = OrderService(db)
    
    orders = await order_service.get_all_orders(
        skip=pagination.skip,
        limit=pagination.limit,
        status=status_filter,
    )
    
    return ResponseModel(
        success=True,
        data=orders,
    )
