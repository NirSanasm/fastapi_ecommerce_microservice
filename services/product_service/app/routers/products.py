"""
Products Router - CRUD operations for products
"""

from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductFilter,
    StockUpdate,
    StockResponse,
)
from app.services.product_service import ProductService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel, PaginationParams


router = APIRouter()


from sqlalchemy.orm import selectinload



@router.get("/", response_model=ResponseModel[List[ProductListResponse]])
async def list_products(
    pagination: PaginationParams = Depends(),
    category_id: Optional[int] = Query(None),
    min_price: Optional[Decimal] = Query(None),
    max_price: Optional[Decimal] = Query(None),
    in_stock_only: bool = Query(False),
    is_featured: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all products with filtering and pagination.
    
    - **category_id**: Filter by category
    - **min_price/max_price**: Price range filter
    - **in_stock_only**: Only show products in stock
    - **is_featured**: Filter featured products
    - **search**: Search in name and description
    - **sort_by**: Sort field (name, price, created_at, stock_quantity)
    - **sort_order**: Sort direction (asc, desc)
    """
    product_filter = ProductFilter(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock_only=in_stock_only,
        is_featured=is_featured,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    product_service = ProductService(db)
    products = await product_service.get_all(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=product_filter,
    )
    
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(products)} products",
        data=products,
    )


@router.get("/{product_id}", response_model=ResponseModel[ProductResponse])
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a product by ID."""
    product_service = ProductService(db)
    product = await product_service.get_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(success=True, data=product)


@router.get("/slug/{slug}", response_model=ResponseModel[ProductResponse])
async def get_product_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a product by slug (URL-friendly identifier)."""
    product_service = ProductService(db)
    product = await product_service.get_by_slug(slug)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(success=True, data=product)


@router.post("/", response_model=ResponseModel[ProductResponse], status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new product.
    
    TODO: Add authentication and require admin/seller role
    """
    product_service = ProductService(db)
    
    # Check for duplicate SKU
    existing = await product_service.get_by_sku(product_data.sku)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists",
        )
    
    product = await product_service.create(product_data)
    product = await product_service.get_with_relations(product.id)
    
    return ResponseModel(
        success=True,
        message="Product created successfully",
        data=product,
    )


@router.put("/{product_id}", response_model=ResponseModel[ProductResponse])
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a product.
    
    TODO: Add authentication and require admin/seller role
    """
    product_service = ProductService(db)
    product = await product_service.update(product_id, product_data)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(
        success=True,
        message="Product updated successfully",
        data=product,
    )


@router.delete("/{product_id}", response_model=ResponseModel)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a product.
    
    TODO: Add authentication and require admin role
    """
    product_service = ProductService(db)
    success = await product_service.delete(product_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(success=True, message="Product deleted successfully")


# ============ Stock Management ============

@router.get("/{product_id}/stock", response_model=ResponseModel[StockResponse])
async def get_product_stock(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get stock information for a product."""
    product_service = ProductService(db)
    stock_info = await product_service.get_stock(product_id)
    
    if not stock_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(success=True, data=stock_info)


@router.put("/{product_id}/stock", response_model=ResponseModel[StockResponse])
async def update_product_stock(
    product_id: int,
    stock_data: StockUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update stock for a product.
    
    - **quantity**: New quantity or adjustment amount
    - **adjustment**: If True, adds/subtracts from current stock
    """
    product_service = ProductService(db)
    stock_info = await product_service.update_stock(product_id, stock_data)
    
    if not stock_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    
    return ResponseModel(
        success=True,
        message="Stock updated successfully",
        data=stock_info,
    )


@router.post("/stock/check", response_model=ResponseModel[List[StockResponse]])
async def check_stock_bulk(
    product_ids: List[int],
    db: AsyncSession = Depends(get_db),
):
    """Check stock for multiple products at once."""
    product_service = ProductService(db)
    stock_info = await product_service.check_stock_bulk(product_ids)
    
    return ResponseModel(success=True, data=stock_info)
