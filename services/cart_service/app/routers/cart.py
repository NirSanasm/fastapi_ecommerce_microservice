"""
Cart Router - Shopping cart operations
"""

from fastapi import APIRouter, HTTPException, status, Header, Response
from typing import Optional
import uuid

from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
    CartSummary,
    CartMerge,
)
from app.config import settings
from app.services.cart_service import CartService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel
from shared.auth import verify_token


router = APIRouter()


def get_user_id(
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
) -> str:
    """
    Extract user ID from authorization header or X-Guest-ID header.
    Supports JWT tokens as well as internal service headers (Bearer user_{id}).
    If unauthenticated, uses persistent X-Guest-ID header if present, or generates a new guest ID.
    """
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        if token.startswith("user_"):
            return token
        try:
            token_data = verify_token(
                token,
                settings.jwt_secret_key,
                settings.jwt_algorithm,
                verify_type="access",
            )
            return f"user_{token_data.user_id}"
        except Exception:
            pass
        if token:
            return f"token_{token[:16]}"
    
    if x_guest_id and x_guest_id.strip():
        gid = x_guest_id.strip()
        return gid if gid.startswith("guest_") else f"guest_{gid}"
    
    # Generate new persistent guest cart ID
    return f"guest_{uuid.uuid4().hex[:8]}"


@router.get("/", response_model=ResponseModel[CartResponse])
async def get_cart(
    response: Response,
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Get current user's or guest's shopping cart.
    """
    user_id = get_user_id(authorization, x_guest_id)
    if user_id.startswith("guest_"):
        response.headers["X-Guest-ID"] = user_id

    cart_service = CartService()
    cart = await cart_service.get_cart(user_id)
    
    return ResponseModel(
        success=True,
        data=cart,
    )


@router.post("/items", response_model=ResponseModel[CartResponse])
async def add_to_cart(
    item: CartItemCreate,
    response: Response,
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Add item to cart.
    
    - **product_id**: Product to add
    - **quantity**: Quantity to add
    """
    user_id = get_user_id(authorization, x_guest_id)
    if user_id.startswith("guest_"):
        response.headers["X-Guest-ID"] = user_id

    cart_service = CartService()
    
    try:
        cart = await cart_service.add_item(user_id, item)
        return ResponseModel(
            success=True,
            message="Item added to cart",
            data=cart,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/items/{product_id}", response_model=ResponseModel[CartResponse])
async def update_cart_item(
    product_id: int,
    item: CartItemUpdate,
    response: Response,
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Update item quantity in cart.
    
    - **product_id**: Product to update
    - **quantity**: New quantity
    """
    user_id = get_user_id(authorization, x_guest_id)
    if user_id.startswith("guest_"):
        response.headers["X-Guest-ID"] = user_id

    cart_service = CartService()
    
    try:
        cart = await cart_service.update_item(user_id, product_id, item.quantity)
        return ResponseModel(
            success=True,
            message="Cart updated",
            data=cart,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/items/{product_id}", response_model=ResponseModel[CartResponse])
async def remove_from_cart(
    product_id: int,
    response: Response,
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Remove item from cart.
    """
    user_id = get_user_id(authorization, x_guest_id)
    if user_id.startswith("guest_"):
        response.headers["X-Guest-ID"] = user_id

    cart_service = CartService()
    cart = await cart_service.remove_item(user_id, product_id)
    
    return ResponseModel(
        success=True,
        message="Item removed from cart",
        data=cart,
    )


@router.delete("/", response_model=ResponseModel)
async def clear_cart(
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Clear all items from cart.
    """
    user_id = get_user_id(authorization, x_guest_id)
    cart_service = CartService()
    
    await cart_service.clear_cart(user_id)
    
    return ResponseModel(
        success=True,
        message="Cart cleared",
    )


@router.get("/summary", response_model=ResponseModel[CartSummary])
async def get_cart_summary(
    response: Response,
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Get cart summary for checkout.
    """
    user_id = get_user_id(authorization, x_guest_id)
    if user_id.startswith("guest_"):
        response.headers["X-Guest-ID"] = user_id

    cart_service = CartService()
    summary = await cart_service.get_summary(user_id)
    
    return ResponseModel(
        success=True,
        data=summary,
    )


@router.post("/merge", response_model=ResponseModel[CartResponse])
async def merge_cart(
    merge_data: CartMerge,
    authorization: Optional[str] = Header(None),
):
    """
    Merge guest cart with authenticated user's cart after login.
    """
    user_id = get_user_id(authorization)
    
    if user_id.startswith("guest_") or user_id.startswith("token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Must be authenticated as a registered user to merge carts",
        )
    
    cart_service = CartService()
    
    try:
        cart = await cart_service.merge_carts(merge_data.guest_cart_id, user_id)
        return ResponseModel(
            success=True,
            message="Carts merged successfully",
            data=cart,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/validate", response_model=ResponseModel)
async def validate_cart(
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None, alias="X-Guest-ID"),
):
    """
    Validate cart items (check real-time stock, active status) before checkout.
    """
    user_id = get_user_id(authorization, x_guest_id)
    cart_service = CartService()
    
    validation = await cart_service.validate_cart(user_id)
    
    if not validation["is_valid"]:
        return ResponseModel(
            success=False,
            message="Cart validation failed",
            data=validation,
        )
    
    return ResponseModel(
        success=True,
        message="Cart is valid",
        data=validation,
    )
