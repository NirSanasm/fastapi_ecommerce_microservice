"""
Product Service - Business Logic Layer

TODO: Implement product management logic here.
"""

from typing import Optional, List
from sqlalchemy import select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import re

from app.models.product import Product, ProductImage, Category
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductFilter,
    StockUpdate,
    StockResponse,
)


class ProductService:
    """
    Product service for handling product-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID with images and category."""
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.category),
            )
            .where(Product.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug."""
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.category),
            )
            .where(Product.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        result = await self.db.execute(
            select(Product).where(Product.sku == sku)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[ProductFilter] = None,
    ) -> List[Product]:
        """
        Get all products with filtering and pagination.
        
        TODO: Implement advanced search with full-text search
        TODO: Add caching for frequently accessed products
        """
        query = select(Product).options(
            selectinload(Product.images),
            selectinload(Product.category),
        )
        
        # Apply filters
        if filters:
            conditions = [Product.is_active == True]
            
            if filters.category_id:
                conditions.append(Product.category_id == filters.category_id)
            
            if filters.min_price:
                conditions.append(Product.price >= filters.min_price)
            
            if filters.max_price:
                conditions.append(Product.price <= filters.max_price)
            
            if filters.in_stock_only:
                conditions.append(Product.stock_quantity > 0)
            
            if filters.is_featured is not None:
                conditions.append(Product.is_featured == filters.is_featured)
            
            if filters.search:
                search_term = f"%{filters.search}%"
                conditions.append(
                    or_(
                        Product.name.ilike(search_term),
                        Product.description.ilike(search_term),
                    )
                )
            
            query = query.where(and_(*conditions))
            
            # Sorting
            sort_column = getattr(Product, filters.sort_by, Product.created_at)
            if filters.sort_order == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, product_data: ProductCreate) -> Product:
        """
        Create a new product.
        
        TODO: Add image processing/upload
        TODO: Publish product created event
        """
        # Generate slug if not provided
        slug = product_data.slug
        if not slug:
            slug = re.sub(r"[^a-z0-9-]", "", product_data.name.lower().replace(" ", "-"))
        
        # Create product
        product = Product(
            name=product_data.name,
            slug=slug,
            description=product_data.description,
            price=product_data.price,
            compare_at_price=product_data.compare_at_price,
            sku=product_data.sku,
            stock_quantity=product_data.stock_quantity,
            low_stock_threshold=product_data.low_stock_threshold,
            category_id=product_data.category_id,
            is_featured=product_data.is_featured,
            weight=product_data.weight,
            dimensions=product_data.dimensions,
        )
        
        self.db.add(product)
        await self.db.flush()
        
        # Add images
        for img_data in product_data.images:
            image = ProductImage(
                product_id=product.id,
                url=img_data.url,
                alt_text=img_data.alt_text,
                position=img_data.position,
                is_primary=img_data.is_primary,
            )
            self.db.add(image)
        
        await self.db.flush()
        await self.db.refresh(product)
        
        return product
    
    async def update(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Update a product."""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        update_dict = product_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(product, field, value)
        
        await self.db.flush()
        await self.db.refresh(product)
        
        return product
    
    async def delete(self, product_id: int) -> bool:
        """Delete a product."""
        product = await self.get_by_id(product_id)
        if not product:
            return False
        
        await self.db.delete(product)
        await self.db.flush()
        
        return True
    
    async def get_stock(self, product_id: int) -> Optional[StockResponse]:
        """Get stock information for a product."""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        return StockResponse(
            product_id=product.id,
            sku=product.sku,
            stock_quantity=product.stock_quantity,
            is_in_stock=product.is_in_stock,
            is_low_stock=product.is_low_stock,
            low_stock_threshold=product.low_stock_threshold,
        )
    
    async def update_stock(
        self,
        product_id: int,
        stock_data: StockUpdate,
    ) -> Optional[StockResponse]:
        """
        Update stock for a product.
        
        TODO: Publish inventory events (low stock, out of stock)
        TODO: Log stock changes for audit
        """
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        if stock_data.adjustment:
            product.stock_quantity += stock_data.quantity
        else:
            product.stock_quantity = stock_data.quantity
        
        # Ensure stock doesn't go negative
        if product.stock_quantity < 0:
            product.stock_quantity = 0
        
        await self.db.flush()
        
        return StockResponse(
            product_id=product.id,
            sku=product.sku,
            stock_quantity=product.stock_quantity,
            is_in_stock=product.is_in_stock,
            is_low_stock=product.is_low_stock,
            low_stock_threshold=product.low_stock_threshold,
        )
    
    async def check_stock_bulk(self, product_ids: List[int]) -> List[StockResponse]:
        """Check stock for multiple products."""
        result = await self.db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = result.scalars().all()
        
        return [
            StockResponse(
                product_id=p.id,
                sku=p.sku,
                stock_quantity=p.stock_quantity,
                is_in_stock=p.is_in_stock,
                is_low_stock=p.is_low_stock,
                low_stock_threshold=p.low_stock_threshold,
            )
            for p in products
        ]
    
    async def reserve_stock(self, product_id: int, quantity: int) -> bool:
        """
        Reserve stock for an order.
        
        TODO: Implement stock reservation with locking
        TODO: Add expiration for reserved stock
        """
        product = await self.get_by_id(product_id)
        if not product or product.stock_quantity < quantity:
            return False
        
        product.stock_quantity -= quantity
        await self.db.flush()
        
        return True
    
    async def release_stock(self, product_id: int, quantity: int) -> bool:
        """Release reserved stock (e.g., order cancelled)."""
        product = await self.get_by_id(product_id)
        if not product:
            return False
        
        product.stock_quantity += quantity
        await self.db.flush()
        
        return True
