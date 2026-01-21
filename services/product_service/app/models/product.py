"""
Product, Category, and Inventory SQLAlchemy Models
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.database import Base


class Category(Base):
    """
    Product category model.
    
    Supports hierarchical categories with parent_id.
    """
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Hierarchical categories
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent"
    )
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name})>"


class Product(Base):
    """
    Product model for the catalog.
    
    Attributes:
        id: Primary key
        name: Product name
        slug: URL-friendly slug
        description: Product description
        price: Product price
        compare_at_price: Original price for showing discounts
        sku: Stock keeping unit (unique identifier)
        category_id: Associated category
        stock_quantity: Available inventory
        is_active: Whether product is visible
    """
    
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    compare_at_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Inventory
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)
    
    # Category
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "10x20x5 cm"
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    
    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below threshold."""
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def discount_percentage(self) -> Optional[float]:
        """Calculate discount percentage if compare_at_price is set."""
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((1 - float(self.price) / float(self.compare_at_price)) * 100, 1)
        return None
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name}, sku={self.sku})>"


class ProductImage(Base):
    """
    Product image model for storing multiple images per product.
    """
    
    __tablename__ = "product_images"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)  # For ordering
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship
    product: Mapped["Product"] = relationship("Product", back_populates="images")
    
    def __repr__(self) -> str:
        return f"<ProductImage(id={self.id}, product_id={self.product_id})>"
