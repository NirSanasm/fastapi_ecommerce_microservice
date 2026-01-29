"""
Order Service - Business Logic Layer

Handles order creation, status management, and integrations with:
- Cart Service (fetch items, clear cart)
- Product Service (validate stock)
- Payment Service (refunds)
- Notification Service (emails)
- RabbitMQ (event publishing)
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import json
import uuid
import logging
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderItemCreate
from app.config import settings
from app.events import event_publisher

logger = logging.getLogger(__name__)


class OrderService:
    """
    Order service for handling order-related business logic.
    
    Integrations:
    - Cart Service: fetches items, clears cart after order
    - Product Service: validates stock availability
    - Payment Service: processes refunds on cancellation
    - Notification Service: sends order emails
    - RabbitMQ: publishes order events
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _generate_order_number(self) -> str:
        """Generate unique order number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"ORD-{timestamp}-{unique_id}"
    
    async def get_order(self, order_id: int, user_id: Optional[int] = None) -> Optional[Order]:
        """Get order by ID with optional user validation."""
        query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_order_number(
        self,
        order_number: str,
        user_id: Optional[int] = None,
    ) -> Optional[Order]:
        """Get order by order number."""
        query = select(Order).options(selectinload(Order.items)).where(Order.order_number == order_number)
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """Get all orders for a user."""
        query = select(Order).options(selectinload(Order.items)).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 10,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """Get all orders (admin)."""
        query = select(Order).options(selectinload(Order.items))
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_order(self, user_id: int, order_data: OrderCreate) -> Order:
        """
        Create a new order.
        
        Steps:
        1. Get items from cart or use provided items
        2. Validate stock availability
        3. Create order with items
        4. Clear cart
        5. Publish order.created event
        """
        # Get items from cart or use provided items
        if order_data.items:
            items = order_data.items
        else:
            items = await self._get_cart_items(user_id)
            if not items:
                raise ValueError("Cart is empty")
        
        # Validate stock availability
        stock_valid = await self._validate_stock(items)
        if not stock_valid:
            raise ValueError("Some items are out of stock")
        
        # Calculate totals
        subtotal = sum(item.unit_price * item.quantity for item in items)
        tax = subtotal * Decimal("0.08")  # 8% tax
        shipping = Decimal("5.99") if subtotal < 50 else Decimal("0")
        total = subtotal + tax + shipping
        
        # Create order
        order = Order(
            order_number=self._generate_order_number(),
            user_id=user_id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            shipping_address=order_data.shipping_address.model_dump_json(),
            billing_address=order_data.billing_address.model_dump_json() if order_data.billing_address else None,
            subtotal=subtotal,
            tax=tax.quantize(Decimal("0.01")),
            shipping_cost=shipping,
            discount=Decimal("0"),
            total=total.quantize(Decimal("0.01")),
            payment_method=order_data.payment_method,
            customer_notes=order_data.customer_notes,
        )
        
        self.db.add(order)
        await self.db.flush()
        
        # Add order items
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product_name,
                product_sku=item.product_sku,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total_price=item.unit_price * item.quantity,
            )
            self.db.add(order_item)
        
        await self.db.flush()
        
        # Re-fetch order with items eagerly loaded to avoid lazy loading issues
        # This prevents MissingGreenlet errors during response serialization
        query = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
        result = await self.db.execute(query)
        order = result.scalar_one()
        
        # Clear cart after order creation
        await self._clear_cart(user_id)
        
        # Publish order.created event
        await event_publisher.publish_order_created(
            order_id=order.id,
            order_number=order.order_number,
            user_id=user_id,
            total=order.total,
            items_count=len(items),
        )
        
        # Send order confirmation notification
        await self._send_notification(
            user_id=user_id,
            notification_type="order_confirmation",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "total": str(order.total),
            }
        )
        
        return order
    
    async def update_status(self, order_id: int, new_status: OrderStatus) -> Optional[Order]:
        """Update order status."""
        order = await self.get_order(order_id)
        if not order:
            return None
        
        old_status = order.status
        order.status = new_status
        
        # Update timestamps based on status
        if new_status == OrderStatus.SHIPPED:
            order.shipped_at = datetime.utcnow()
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(order)
        
        # Publish order.status_updated event
        await event_publisher.publish_order_status_updated(
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            old_status=old_status.value,
            new_status=new_status.value,
        )
        
        # Send notification to customer
        await self._send_notification(
            user_id=order.user_id,
            notification_type="order_status_update",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "old_status": old_status.value,
                "new_status": new_status.value,
            }
        )
        
        return order
    
    async def add_tracking(
        self,
        order_id: int,
        tracking_number: str,
        carrier: str,
    ) -> Optional[Order]:
        """Add tracking information to order."""
        order = await self.get_order(order_id)
        if not order:
            return None
        
        order.tracking_number = tracking_number
        order.carrier = carrier
        
        # Auto-update status to shipped if pending/confirmed
        if order.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            order.status = OrderStatus.SHIPPED
            order.shipped_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(order)
        
        # Publish order.shipped event
        await event_publisher.publish_order_shipped(
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            tracking_number=tracking_number,
            carrier=carrier,
        )
        
        # Send shipping notification
        await self._send_notification(
            user_id=order.user_id,
            notification_type="order_shipped",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "tracking_number": tracking_number,
                "carrier": carrier,
            }
        )
        
        return order
    
    async def cancel_order(self, order_id: int, user_id: int) -> Order:
        """
        Cancel an order.
        
        Steps:
        1. Validate order can be cancelled
        2. Update status to cancelled
        3. Release reserved inventory
        4. Process refund if payment was made
        5. Publish order.cancelled event
        """
        order = await self.get_order(order_id, user_id)
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot cancel order in {order.status.value} status")
        
        order.status = OrderStatus.CANCELLED
        
        # Release reserved inventory (via product service)
        await self._release_inventory(order)
        
        # Process refund if payment was made
        if order.payment_status == PaymentStatus.COMPLETED and order.payment_id:
            await self._request_refund(order.payment_id, order.total)
            order.payment_status = PaymentStatus.REFUNDED
        
        await self.db.flush()
        await self.db.refresh(order)
        
        # Publish order.cancelled event
        await event_publisher.publish_order_cancelled(
            order_id=order.id,
            order_number=order.order_number,
            user_id=user_id,
            reason="Customer requested cancellation",
        )
        
        # Send cancellation notification
        await self._send_notification(
            user_id=user_id,
            notification_type="order_cancelled",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
            }
        )
        
        return order
    
    async def process_payment_success(self, order_id: int, payment_id: str) -> Optional[Order]:
        """
        Handle successful payment.
        
        Called by payment service webhook.
        """
        order = await self.get_order(order_id)
        if not order:
            return None
        
        order.payment_status = PaymentStatus.COMPLETED
        order.payment_id = payment_id
        order.status = OrderStatus.CONFIRMED
        
        await self.db.flush()
        await self.db.refresh(order)
        
        # Publish order.confirmed event
        await event_publisher.publish_order_confirmed(
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            payment_id=payment_id,
        )
        
        return order
    
    async def process_payment_failure(self, order_id: int) -> Optional[Order]:
        """Handle failed payment."""
        order = await self.get_order(order_id)
        if not order:
            return None
        
        order.payment_status = PaymentStatus.FAILED
        
        # Release reserved inventory
        await self._release_inventory(order)
        
        await self.db.flush()
        await self.db.refresh(order)
        
        # Send payment failure notification
        await self._send_notification(
            user_id=order.user_id,
            notification_type="payment_failed",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
            }
        )
        
        return order
    
    # =============================================================================
    # Service Integration Methods
    # =============================================================================
    
    async def _get_cart_items(self, user_id: int) -> List[OrderItemCreate]:
        """Fetch cart items from cart service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.cart_service_url}/api/v1/cart",
                    headers={"Authorization": f"Bearer user_{user_id}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    cart_items = data.get("data", {}).get("items", [])
                    return [
                        OrderItemCreate(
                            product_id=item["product_id"],
                            product_name=item.get("product_name", f"Product {item['product_id']}"),
                            product_sku=item.get("product_sku", f"SKU-{item['product_id']}"),
                            unit_price=Decimal(str(item.get("unit_price", item.get("price", "0")))),
                            quantity=item["quantity"],
                        )
                        for item in cart_items
                    ]
        except Exception as e:
            logger.error(f"Error fetching cart: {e}")
        return []
    
    async def _clear_cart(self, user_id: int) -> bool:
        """Clear user's cart after order creation."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"{settings.cart_service_url}/api/v1/cart",
                    headers={"Authorization": f"Bearer user_{user_id}"},
                )
                if response.status_code == 200:
                    logger.info(f"Cart cleared for user {user_id}")
                    return True
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
        return False
    
    async def _validate_stock(self, items: List[OrderItemCreate]) -> bool:
        """Validate product stock availability via product service."""
        try:
            product_ids = [item.product_id for item in items]
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.product_service_url}/api/v1/products/stock/check",
                    json=product_ids,
                )
                if response.status_code == 200:
                    data = response.json()
                    stock_data = data.get("data", [])
                    # Check if all items have sufficient stock
                    for item in items:
                        stock_info = next(
                            (s for s in stock_data if s.get("product_id") == item.product_id),
                            None
                        )
                        if not stock_info or stock_info.get("stock_quantity", 0) < item.quantity:
                            return False
                    return True
        except Exception as e:
            logger.error(f"Error validating stock: {e}")
        # Default to true if product service unavailable (graceful degradation)
        return True
    
    async def _release_inventory(self, order: Order) -> bool:
        """Release reserved inventory when order is cancelled."""
        try:
            for item in order.items:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Add stock back
                    response = await client.put(
                        f"{settings.product_service_url}/api/v1/products/{item.product_id}/stock",
                        json={"quantity": item.quantity, "adjustment": True},
                    )
                    if response.status_code != 200:
                        logger.warning(f"Failed to release stock for product {item.product_id}")
            return True
        except Exception as e:
            logger.error(f"Error releasing inventory: {e}")
        return False
    
    async def _request_refund(self, payment_id: str, amount: Decimal) -> bool:
        """Request refund through payment service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.payment_service_url}/api/v1/payments/refund",
                    json={
                        "payment_id": int(payment_id) if payment_id.isdigit() else payment_id,
                        "amount": float(amount),
                        "reason": "Order cancelled by customer",
                    },
                )
                if response.status_code == 200:
                    logger.info(f"Refund processed for payment {payment_id}")
                    return True
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
        return False
    
    async def _send_notification(
        self,
        user_id: int,
        notification_type: str,
        data: dict,
    ) -> bool:
        """Send notification through notification service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.notification_service_url}/api/v1/notifications/send",
                    json={
                        "user_id": user_id,
                        "type": notification_type,
                        "data": data,
                    },
                )
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Notification {notification_type} sent to user {user_id}")
                    return True
        except Exception as e:
            logger.warning(f"Error sending notification: {e}")
        # Don't fail order if notification fails
        return False
