"""
Cart Service - Business Logic Layer

TODO: Implement cart management logic here.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import httpx

from app.redis_client import redis_client
from app.schemas.cart import (
    CartItemCreate,
    CartResponse,
    CartItemResponse,
    CartSummary,
)
from app.config import settings


class CartService:
    """
    Cart service for handling shopping cart operations.
    
    TODO: Add product service integration for real-time prices
    TODO: Add stock validation before checkout
    """
    
    def __init__(self):
        self.redis = redis_client
    
    async def get_cart(self, user_id: str) -> CartResponse:
        """
        Get user's cart with product details.
        
        TODO: Fetch real product data from Product Service
        """
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        # Enrich items with product details
        enriched_items = []
        subtotal = Decimal("0")
        
        for item in items:
            # TODO: Fetch product details from Product Service
            # product = await self._get_product(item["product_id"])
            
            # Placeholder product data
            product = {
                "name": f"Product {item['product_id']}",
                "sku": f"SKU{item['product_id']:05d}",
                "price": Decimal("29.99"),
                "stock": 100,
                "image_url": None,
            }
            
            item_total = product["price"] * item["quantity"]
            subtotal += item_total
            
            enriched_items.append(CartItemResponse(
                product_id=item["product_id"],
                product_name=product["name"],
                product_sku=product["sku"],
                quantity=item["quantity"],
                unit_price=product["price"],
                total_price=item_total,
                in_stock=product["stock"] >= item["quantity"],
                stock_available=product["stock"],
                image_url=product["image_url"],
            ))
        
        return CartResponse(
            user_id=user_id,
            items=enriched_items,
            item_count=sum(item.quantity for item in enriched_items),
            subtotal=subtotal,
            updated_at=cart_data.get("updated_at"),
        )
    
    async def add_item(
        self,
        user_id: str,
        item: CartItemCreate,
    ) -> CartResponse:
        """
        Add item to cart or update quantity if exists.
        
        TODO: Validate product exists and is in stock
        """
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        # Check if item already in cart
        existing_item = next(
            (i for i in items if i["product_id"] == item.product_id),
            None
        )
        
        if existing_item:
            existing_item["quantity"] += item.quantity
        else:
            items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
            })
        
        cart_data["items"] = items
        cart_data["updated_at"] = datetime.utcnow().isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def update_item(
        self,
        user_id: str,
        product_id: int,
        quantity: int,
    ) -> CartResponse:
        """Update item quantity in cart."""
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        item = next(
            (i for i in items if i["product_id"] == product_id),
            None
        )
        
        if not item:
            raise ValueError("Item not found in cart")
        
        item["quantity"] = quantity
        cart_data["updated_at"] = datetime.utcnow().isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def remove_item(self, user_id: str, product_id: int) -> CartResponse:
        """Remove item from cart."""
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        cart_data["items"] = [
            i for i in items if i["product_id"] != product_id
        ]
        cart_data["updated_at"] = datetime.utcnow().isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def clear_cart(self, user_id: str) -> bool:
        """Clear all items from cart."""
        return await self.redis.delete_cart(user_id)
    
    async def get_summary(self, user_id: str) -> CartSummary:
        """
        Get cart summary with tax and shipping.
        
        TODO: Implement tax calculation based on location
        TODO: Implement shipping calculation based on items and location
        """
        cart = await self.get_cart(user_id)
        
        subtotal = cart.subtotal
        tax = subtotal * Decimal("0.08")  # 8% tax placeholder
        shipping = Decimal("5.99") if subtotal < Decimal("50") else Decimal("0")
        total = subtotal + tax + shipping
        
        return CartSummary(
            item_count=cart.item_count,
            subtotal=subtotal,
            tax=tax.quantize(Decimal("0.01")),
            shipping=shipping,
            total=total.quantize(Decimal("0.01")),
        )
    
    async def merge_carts(
        self,
        guest_cart_id: str,
        user_id: str,
    ) -> CartResponse:
        """
        Merge guest cart with user cart after login.
        
        TODO: Handle conflicts (same product in both carts)
        """
        guest_cart = await self.redis.get_cart(guest_cart_id)
        user_cart = await self.redis.get_cart(user_id)
        
        guest_items = guest_cart.get("items", [])
        user_items = user_cart.get("items", [])
        
        # Merge items
        for guest_item in guest_items:
            existing = next(
                (i for i in user_items if i["product_id"] == guest_item["product_id"]),
                None
            )
            if existing:
                existing["quantity"] += guest_item["quantity"]
            else:
                user_items.append(guest_item)
        
        user_cart["items"] = user_items
        user_cart["updated_at"] = datetime.utcnow().isoformat()
        
        await self.redis.save_cart(user_id, user_cart)
        await self.redis.delete_cart(guest_cart_id)
        
        return await self.get_cart(user_id)
    
    async def validate_cart(self, user_id: str) -> dict:
        """
        Validate cart before checkout.
        
        TODO: Check product availability with Product Service
        TODO: Check price changes
        """
        cart = await self.get_cart(user_id)
        
        issues = []
        is_valid = True
        
        for item in cart.items:
            if not item.in_stock:
                is_valid = False
                issues.append({
                    "product_id": item.product_id,
                    "issue": "out_of_stock",
                    "message": f"{item.product_name} is out of stock",
                })
            elif item.stock_available < item.quantity:
                is_valid = False
                issues.append({
                    "product_id": item.product_id,
                    "issue": "insufficient_stock",
                    "message": f"Only {item.stock_available} available for {item.product_name}",
                    "available": item.stock_available,
                })
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "item_count": cart.item_count,
            "subtotal": str(cart.subtotal),
        }
    
    async def _get_product(self, product_id: int) -> Optional[dict]:
        """
        Fetch product details from Product Service.
        
        TODO: Implement product service integration
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.product_service_url}/api/v1/products/{product_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data")
        except Exception as e:
            print(f"Error fetching product: {e}")
        return None
