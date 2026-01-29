"""
Orders Router - Order management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.database import get_db
from app.config import settings
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
from shared.auth import verify_token, TokenData


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    Extract and validate user from JWT token.
    
    Returns:
        TokenData with user_id and roles
    """
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
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    Require admin role for access.
    
    Raises:
        HTTPException: If user doesn't have admin role
    """
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/", response_model=ResponseModel[OrderResponse], status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order from cart.
    
    - Uses items from cart if items not provided
    - Validates stock availability
    - Creates payment intent
    """
    user_id = int(current_user.user_id)
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
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's orders with optional filtering.
    """
    user_id = int(current_user.user_id)
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
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order details by ID.
    """
    user_id = int(current_user.user_id)
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
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order details by order number.
    """
    user_id = int(current_user.user_id)
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
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an order (only if pending/confirmed).
    """
    user_id = int(current_user.user_id)
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
    admin_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update order status (admin only).
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
    admin_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Add tracking information to order (admin only).
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
    admin_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all orders (admin only).
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
