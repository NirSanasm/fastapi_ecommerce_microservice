"""
Product Pydantic Schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
import re


# ============ Category Schemas ============

class CategoryBase(BaseModel):
    """Base category schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    slug: Optional[str] = None  # Auto-generated if not provided
    
    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v, info):
        """Generate slug from name if not provided."""
        if v is None and "name" in info.data:
            # Simple slug generation - replace spaces with hyphens, lowercase
            return re.sub(r"[^a-z0-9-]", "", info.data["name"].lower().replace(" ", "-"))
        return v


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    id: int
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    """Category response with nested children."""
    children: List["CategoryWithChildren"] = []


# ============ Product Image Schemas ============

class ProductImageBase(BaseModel):
    """Base product image schema."""
    url: str
    alt_text: Optional[str] = None
    position: int = 0
    is_primary: bool = False


class ProductImageCreate(ProductImageBase):
    """Schema for adding product image."""
    pass


class ProductImageResponse(ProductImageBase):
    """Schema for product image response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Product Schemas ============

class ProductBase(BaseModel):
    """Base product schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    sku: str = Field(..., min_length=1, max_length=100)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    category_id: Optional[int] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    slug: Optional[str] = None
    is_featured: bool = False
    images: List[ProductImageCreate] = []
    
    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v, info):
        """Generate slug from name if not provided."""
        if v is None and "name" in info.data:
            return re.sub(r"[^a-z0-9-]", "", info.data["name"].lower().replace(" ", "-"))
        return v


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: int
    slug: str
    is_active: bool
    is_featured: bool
    is_in_stock: bool
    is_low_stock: bool
    discount_percentage: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[CategoryResponse] = None
    images: List[ProductImageResponse] = []
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for product list with pagination."""
    id: int
    name: str
    slug: str
    price: Decimal
    compare_at_price: Optional[Decimal] = None
    sku: str
    stock_quantity: int
    is_active: bool
    is_featured: bool
    is_in_stock: bool
    discount_percentage: Optional[float] = None
    primary_image: Optional[str] = None
    category_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============ Inventory Schemas ============

class StockUpdate(BaseModel):
    """Schema for updating stock quantity."""
    quantity: int = Field(..., description="New stock quantity or adjustment")
    adjustment: bool = Field(
        default=False,
        description="If True, quantity is added/subtracted from current. If False, it replaces."
    )
    reason: Optional[str] = Field(None, description="Reason for stock change")


class StockResponse(BaseModel):
    """Schema for stock check response."""
    product_id: int
    sku: str
    stock_quantity: int
    is_in_stock: bool
    is_low_stock: bool
    low_stock_threshold: int


# ============ Search/Filter Schemas ============

class ProductFilter(BaseModel):
    """Schema for product filtering."""
    category_id: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock_only: bool = False
    is_featured: Optional[bool] = None
    search: Optional[str] = None
    sort_by: str = Field(default="created_at", pattern="^(name|price|created_at|stock_quantity)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
