"""
Cart Router - Shopping cart operations
"""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional

from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
    CartSummary,
    CartMerge,
)
from app.services.cart_service import CartService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel


router = APIRouter()


def get_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from authorization header.
    
    TODO: Implement proper JWT validation
    For now, uses a placeholder user ID or guest ID
    """
    if authorization:
        # TODO: Decode JWT and extract user ID
        # token = authorization.replace("Bearer ", "")
        # user_id = decode_token(token).user_id
        return "user_123"  # Placeholder
    
    # Generate guest cart ID
    import uuid
    return f"guest_{uuid.uuid4().hex[:8]}"


@router.get("/", response_model=ResponseModel[CartResponse])
async def get_cart(
    authorization: Optional[str] = Header(None),
):
    """
    Get current user's shopping cart.
    """
    user_id = get_user_id(authorization)
    cart_service = CartService()
    
    cart = await cart_service.get_cart(user_id)
    
    return ResponseModel(
        success=True,
        data=cart,
    )


@router.post("/items", response_model=ResponseModel[CartResponse])
async def add_to_cart(
    item: CartItemCreate,
    authorization: Optional[str] = Header(None),
):
    """
    Add item to cart.
    
    - **product_id**: Product to add
    - **quantity**: Quantity to add
    """
    user_id = get_user_id(authorization)
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
    authorization: Optional[str] = Header(None),
):
    """
    Update item quantity in cart.
    
    - **product_id**: Product to update
    - **quantity**: New quantity
    """
    user_id = get_user_id(authorization)
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
    authorization: Optional[str] = Header(None),
):
    """
    Remove item from cart.
    """
    user_id = get_user_id(authorization)
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
):
    """
    Clear all items from cart.
    """
    user_id = get_user_id(authorization)
    cart_service = CartService()
    
    await cart_service.clear_cart(user_id)
    
    return ResponseModel(
        success=True,
        message="Cart cleared",
    )


@router.get("/summary", response_model=ResponseModel[CartSummary])
async def get_cart_summary(
    authorization: Optional[str] = Header(None),
):
    """
    Get cart summary for checkout.
    """
    user_id = get_user_id(authorization)
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
    Merge guest cart with user cart after login.
    
    TODO: Implement cart merging logic
    """
    user_id = get_user_id(authorization)
    
    if user_id.startswith("guest_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Must be authenticated to merge carts",
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
):
    """
    Validate cart items (check stock, prices) before checkout.
    """
    user_id = get_user_id(authorization)
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
