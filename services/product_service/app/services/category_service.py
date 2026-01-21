"""
Category Service - Business Logic Layer
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import re

from app.models.product import Category
from app.schemas.product import CategoryCreate, CategoryUpdate


class CategoryService:
    """Category service for handling category-related business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        result = await self.db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, include_inactive: bool = False) -> List[Category]:
        """Get all categories."""
        query = select(Category)
        if not include_inactive:
            query = query.where(Category.is_active == True)
        query = query.order_by(Category.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_tree(self) -> List[Category]:
        """
        Get categories as a hierarchical tree.
        
        TODO: Implement efficient tree building
        """
        # Get all root categories (no parent)
        result = await self.db.execute(
            select(Category)
            .options(selectinload(Category.children))
            .where(Category.parent_id.is_(None))
            .where(Category.is_active == True)
            .order_by(Category.name)
        )
        return list(result.scalars().all())
    
    async def create(self, category_data: CategoryCreate) -> Category:
        """Create a new category."""
        slug = category_data.slug
        if not slug:
            slug = re.sub(r"[^a-z0-9-]", "", category_data.name.lower().replace(" ", "-"))
        
        category = Category(
            name=category_data.name,
            slug=slug,
            description=category_data.description,
            image_url=category_data.image_url,
            parent_id=category_data.parent_id,
        )
        
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        
        return category
    
    async def update(self, category_id: int, category_data: CategoryUpdate) -> Optional[Category]:
        """Update a category."""
        category = await self.get_by_id(category_id)
        if not category:
            return None
        
        update_dict = category_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(category, field, value)
        
        await self.db.flush()
        await self.db.refresh(category)
        
        return category
    
    async def delete(self, category_id: int) -> bool:
        """Delete a category."""
        category = await self.get_by_id(category_id)
        if not category:
            return False
        
        await self.db.delete(category)
        await self.db.flush()
        
        return True
