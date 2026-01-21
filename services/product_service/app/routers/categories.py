"""
Categories Router - CRUD operations for categories
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.product import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithChildren,
)
from app.services.category_service import CategoryService

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.schemas import ResponseModel


router = APIRouter()


@router.get("/", response_model=ResponseModel[List[CategoryResponse]])
async def list_categories(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    List all categories.
    
    - **include_inactive**: Include inactive categories (admin only)
    """
    category_service = CategoryService(db)
    categories = await category_service.get_all(include_inactive=include_inactive)
    
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(categories)} categories",
        data=categories,
    )


@router.get("/tree", response_model=ResponseModel[List[CategoryWithChildren]])
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
):
    """Get categories as a hierarchical tree structure."""
    category_service = CategoryService(db)
    tree = await category_service.get_tree()
    
    return ResponseModel(success=True, data=tree)


@router.get("/{category_id}", response_model=ResponseModel[CategoryResponse])
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a category by ID."""
    category_service = CategoryService(db)
    category = await category_service.get_by_id(category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return ResponseModel(success=True, data=category)


@router.get("/slug/{slug}", response_model=ResponseModel[CategoryResponse])
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a category by slug."""
    category_service = CategoryService(db)
    category = await category_service.get_by_slug(slug)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return ResponseModel(success=True, data=category)


@router.post("/", response_model=ResponseModel[CategoryResponse], status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new category.
    
    TODO: Add authentication and require admin role
    """
    category_service = CategoryService(db)
    
    # Check for duplicate name
    existing = await category_service.get_by_slug(
        category_data.slug or category_data.name.lower().replace(" ", "-")
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )
    
    category = await category_service.create(category_data)
    
    return ResponseModel(
        success=True,
        message="Category created successfully",
        data=category,
    )


@router.put("/{category_id}", response_model=ResponseModel[CategoryResponse])
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a category.
    
    TODO: Add authentication and require admin role
    """
    category_service = CategoryService(db)
    category = await category_service.update(category_id, category_data)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return ResponseModel(
        success=True,
        message="Category updated successfully",
        data=category,
    )


@router.delete("/{category_id}", response_model=ResponseModel)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a category.
    
    TODO: Add authentication and require admin role
    """
    category_service = CategoryService(db)
    success = await category_service.delete(category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return ResponseModel(success=True, message="Category deleted successfully")
