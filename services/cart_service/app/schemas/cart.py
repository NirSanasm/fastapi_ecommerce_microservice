"""
Cart Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    """Schema for adding item to cart."""
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity to add")


class CartItemUpdate(BaseModel):
    """Schema for updating cart item."""
    quantity: int = Field(..., gt=0, description="New quantity")


class CartItemResponse(BaseModel):
    """Schema for cart item response."""
    product_id: int
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    in_stock: bool
    stock_available: int
    image_url: Optional[str] = None


class CartResponse(BaseModel):
    """Schema for complete cart response."""
    user_id: str
    items: List[CartItemResponse]
    item_count: int
    subtotal: Decimal
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123",
                "items": [
                    {
                        "product_id": 1,
                        "product_name": "Sample Product",
                        "product_sku": "SKU001",
                        "quantity": 2,
                        "unit_price": "29.99",
                        "total_price": "59.98",
                        "in_stock": True,
                        "stock_available": 10,
                    }
                ],
                "item_count": 2,
                "subtotal": "59.98",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        }


class CartSummary(BaseModel):
    """Summary of cart for checkout."""
    item_count: int
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal


class CartMerge(BaseModel):
    """Schema for merging guest cart with user cart."""
    guest_cart_id: str
