"""
Order Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentStatus


class AddressSchema(BaseModel):
    """Address schema for shipping/billing."""
    first_name: str
    last_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    phone: Optional[str] = None


class OrderItemCreate(BaseModel):
    """Schema for order item in create request."""
    product_id: int
    product_name: str
    product_sku: str
    unit_price: Decimal
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Schema for order item response."""
    id: int
    product_id: int
    product_name: str
    product_sku: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Schema for creating an order."""
    shipping_address: AddressSchema
    billing_address: Optional[AddressSchema] = None
    payment_method: str = "stripe"
    customer_notes: Optional[str] = None
    
    # Items can be provided or pulled from cart
    items: Optional[List[OrderItemCreate]] = None


class OrderUpdate(BaseModel):
    """Schema for updating order (admin)."""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    internal_notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: int
    order_number: str
    user_id: int
    status: OrderStatus
    payment_status: PaymentStatus
    
    shipping_address: str  # JSON string
    billing_address: Optional[str] = None
    
    subtotal: Decimal
    tax: Decimal
    shipping_cost: Decimal
    discount: Decimal
    total: Decimal
    
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None
    
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    
    customer_notes: Optional[str] = None
    
    items: List[OrderItemResponse] = []
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for order list with pagination."""
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    total: Decimal
    item_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status only."""
    status: OrderStatus
    notes: Optional[str] = None


class TrackingUpdate(BaseModel):
    """Schema for adding tracking information."""
    tracking_number: str
    carrier: str
