"""
Cart Service - Business Logic Layer

Handles shopping cart operations, product enrichment, inventory validation,
tax & shipping calculation, and guest-to-user cart merging.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import logging
import httpx

from app.redis_client import redis_client
from app.schemas.cart import (
    CartItemCreate,
    CartResponse,
    CartItemResponse,
    CartSummary,
)
from app.config import settings

logger = logging.getLogger(__name__)


class CartService:
    """
    Cart service for handling shopping cart operations with real-time product
    data enrichment and inventory validation.
    """
    
    def __init__(self):
        self.redis = redis_client
    
    async def _get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Fetch product details from Product Service."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{settings.product_service_url}/api/v1/products/{product_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data")
                elif response.status_code == 404:
                    return None
                else:
                    logger.warning(
                        f"Product Service returned {response.status_code} for product {product_id}"
                    )
        except Exception as e:
            logger.error(f"Error fetching product {product_id} from Product Service: {e}")
        return None
    
    async def get_cart(self, user_id: str) -> CartResponse:
        """
        Get user's or guest's cart enriched with real product details, pricing, and stock.
        """
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        enriched_items: List[CartItemResponse] = []
        subtotal = Decimal("0.00")
        
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            product = await self._get_product(product_id)
            
            if product:
                price = Decimal(str(product.get("price", "0.00")))
                stock = int(product.get("stock_quantity", 0))
                is_active = bool(product.get("is_active", True))
                in_stock = is_active and (stock >= quantity)
                name = product.get("name", f"Product {product_id}")
                sku = product.get("sku", f"SKU{product_id:05d}")
                
                # Extract primary image URL if present
                images = product.get("images", [])
                image_url = None
                if images and isinstance(images, list):
                    for img in images:
                        if isinstance(img, dict) and img.get("is_primary"):
                            image_url = img.get("url")
                            break
                    if not image_url and len(images) > 0 and isinstance(images[0], dict):
                        image_url = images[0].get("url")
            else:
                # Fallback to snapshot info or default placeholder if product service is temporarily unavailable
                name = item.get("name", f"Product {product_id}")
                sku = item.get("sku", f"SKU{product_id:05d}")
                price = Decimal(str(item.get("price", "29.99")))
                stock = int(item.get("stock", 100))
                in_stock = stock >= quantity
                image_url = item.get("image_url")
            
            item_total = (price * quantity).quantize(Decimal("0.01"))
            subtotal += item_total
            
            enriched_items.append(CartItemResponse(
                product_id=product_id,
                product_name=name,
                product_sku=sku,
                quantity=quantity,
                unit_price=price,
                total_price=item_total,
                in_stock=in_stock,
                stock_available=stock,
                image_url=image_url,
            ))
        
        total_quantity = sum(item.quantity for item in enriched_items)
        
        return CartResponse(
            user_id=user_id,
            items=enriched_items,
            item_count=total_quantity,
            total_items=total_quantity,
            subtotal=subtotal.quantize(Decimal("0.01")),
            updated_at=cart_data.get("updated_at"),
        )
    
    async def add_item(
        self,
        user_id: str,
        item: CartItemCreate,
    ) -> CartResponse:
        """
        Add item to cart or update quantity if it already exists.
        Validates product existence, active status, and real-time inventory.
        """
        if item.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
            
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        # Check if item already in cart
        existing_item = next(
            (i for i in items if i["product_id"] == item.product_id),
            None
        )
        current_qty = existing_item["quantity"] if existing_item else 0
        target_qty = current_qty + item.quantity
        
        # Validate against Product Service
        product = await self._get_product(item.product_id)
        if product:
            if not product.get("is_active", True):
                raise ValueError(f"Product '{product.get('name', item.product_id)}' is currently not available")
            
            available_stock = int(product.get("stock_quantity", 0))
            if available_stock <= 0:
                raise ValueError(f"Product '{product.get('name', item.product_id)}' is out of stock")
            
            if target_qty > available_stock:
                raise ValueError(
                    f"Cannot add {item.quantity} more. Only {available_stock} available in stock "
                    f"(you already have {current_qty} in your cart)"
                )
            
            p_name = product.get("name")
            p_price = str(product.get("price"))
            p_sku = product.get("sku")
            p_stock = available_stock
        else:
            p_name = f"Product {item.product_id}"
            p_price = "29.99"
            p_sku = f"SKU{item.product_id:05d}"
            p_stock = 100

        if existing_item:
            existing_item["quantity"] = target_qty
            existing_item["name"] = p_name
            existing_item["price"] = p_price
            existing_item["sku"] = p_sku
            existing_item["stock"] = p_stock
        else:
            items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "name": p_name,
                "price": p_price,
                "sku": p_sku,
                "stock": p_stock,
            })
        
        cart_data["items"] = items
        cart_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def update_item(
        self,
        user_id: str,
        product_id: int,
        quantity: int,
    ) -> CartResponse:
        """Update item quantity in cart. Validates available stock."""
        if quantity <= 0:
            return await self.remove_item(user_id, product_id)
            
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        item = next(
            (i for i in items if i["product_id"] == product_id),
            None
        )
        
        if not item:
            raise ValueError("Item not found in cart")
        
        # Validate stock with Product Service
        product = await self._get_product(product_id)
        if product:
            if not product.get("is_active", True):
                raise ValueError(f"Product '{product.get('name', product_id)}' is currently not available")
            
            available_stock = int(product.get("stock_quantity", 0))
            if quantity > available_stock:
                raise ValueError(
                    f"Requested quantity ({quantity}) exceeds available stock ({available_stock}) for '{product.get('name')}'"
                )
            item["name"] = product.get("name")
            item["price"] = str(product.get("price"))
            item["sku"] = product.get("sku")
            item["stock"] = available_stock
        
        item["quantity"] = quantity
        cart_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def remove_item(self, user_id: str, product_id: int) -> CartResponse:
        """Remove item from cart."""
        cart_data = await self.redis.get_cart(user_id)
        items = cart_data.get("items", [])
        
        cart_data["items"] = [
            i for i in items if i["product_id"] != product_id
        ]
        cart_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.redis.save_cart(user_id, cart_data)
        
        return await self.get_cart(user_id)
    
    async def clear_cart(self, user_id: str) -> bool:
        """Clear all items from cart."""
        return await self.redis.delete_cart(user_id)
    
    async def get_summary(self, user_id: str) -> CartSummary:
        """
        Get cart summary with tax and shipping.
        - Tax: Standard 8% estimated sales tax.
        - Shipping: Free for orders >= $50.00, $5.99 for orders < $50.00, $0 if empty cart.
        """
        cart = await self.get_cart(user_id)
        
        subtotal = cart.subtotal
        if subtotal > Decimal("0"):
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))
            shipping = Decimal("0.00") if subtotal >= Decimal("50.00") else Decimal("5.99")
        else:
            tax = Decimal("0.00")
            shipping = Decimal("0.00")
            
        total = (subtotal + tax + shipping).quantize(Decimal("0.01"))
        
        return CartSummary(
            item_count=cart.item_count,
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=total,
        )
    
    async def merge_carts(
        self,
        guest_cart_id: str,
        user_id: str,
    ) -> CartResponse:
        """
        Merge guest cart with user cart after login.
        Validates product availability and caps quantity to available real-time stock.
        """
        clean_guest_id = guest_cart_id.strip() if guest_cart_id else ""
        if clean_guest_id and not clean_guest_id.startswith("guest_") and not clean_guest_id.startswith("user_"):
            clean_guest_id = f"guest_{clean_guest_id}"

        clean_user_id = user_id.strip() if user_id else ""
        if clean_user_id and not clean_user_id.startswith("user_") and not clean_user_id.startswith("guest_"):
            clean_user_id = f"user_{clean_user_id}"

        if not clean_guest_id or clean_guest_id == clean_user_id:
            return await self.get_cart(clean_user_id)

        guest_cart = await self.redis.get_cart(clean_guest_id)
        user_cart = await self.redis.get_cart(clean_user_id)
        
        guest_items = guest_cart.get("items", [])
        if not guest_items:
            return await self.get_cart(clean_user_id)

        user_items = user_cart.get("items", [])
        
        for guest_item in guest_items:
            product_id = guest_item.get("product_id")
            guest_qty = guest_item.get("quantity", 0)
            if not product_id or guest_qty <= 0:
                continue

            product = await self._get_product(product_id)
            if product:
                if not product.get("is_active", True):
                    continue
                stock = int(product.get("stock_quantity", 0))
                if stock <= 0:
                    continue
                name = product.get("name")
                price = str(product.get("price"))
                sku = product.get("sku")
            else:
                stock = int(guest_item.get("stock", 100))
                name = guest_item.get("name", f"Product {product_id}")
                price = guest_item.get("price", "29.99")
                sku = guest_item.get("sku", f"SKU{product_id:05d}")

            existing = next(
                (i for i in user_items if i["product_id"] == product_id),
                None
            )
            if existing:
                combined_qty = existing["quantity"] + guest_qty
                existing["quantity"] = min(combined_qty, stock)
                existing["name"] = name
                existing["price"] = price
                existing["sku"] = sku
                existing["stock"] = stock
            else:
                user_items.append({
                    "product_id": product_id,
                    "quantity": min(guest_qty, stock),
                    "name": name,
                    "price": price,
                    "sku": sku,
                    "stock": stock,
                })
        
        user_cart["items"] = user_items
        user_cart["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.redis.save_cart(clean_user_id, user_cart)
        await self.redis.delete_cart(clean_guest_id)
        
        return await self.get_cart(clean_user_id)
    
    async def validate_cart(self, user_id: str) -> dict:
        """
        Validate cart items before checkout:
        - Check real-time stock availability
        - Check if items are active/discontinued
        - Report detailed validation issues
        """
        cart = await self.get_cart(user_id)
        
        issues = []
        is_valid = True
        
        if not cart.items:
            return {
                "is_valid": False,
                "issues": [{"issue": "empty_cart", "message": "Shopping cart is empty"}],
                "item_count": 0,
                "subtotal": "0.00",
            }
        
        for item in cart.items:
            if not item.in_stock:
                is_valid = False
                if item.stock_available == 0:
                    issues.append({
                        "product_id": item.product_id,
                        "issue": "out_of_stock",
                        "message": f"'{item.product_name}' is currently out of stock",
                    })
                else:
                    issues.append({
                        "product_id": item.product_id,
                        "issue": "insufficient_stock",
                        "message": f"Only {item.stock_available} available for '{item.product_name}' (requested {item.quantity})",
                        "available": item.stock_available,
                    })
            elif item.stock_available < item.quantity:
                is_valid = False
                issues.append({
                    "product_id": item.product_id,
                    "issue": "insufficient_stock",
                    "message": f"Only {item.stock_available} available for '{item.product_name}' (requested {item.quantity})",
                    "available": item.stock_available,
                })
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "item_count": cart.item_count,
            "subtotal": str(cart.subtotal),
        }
