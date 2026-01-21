"""
Order Service - Business Logic Layer

TODO: Implement order processing logic here.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import json
import uuid
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse
from app.config import settings


class OrderService:
    """
    Order service for handling order-related business logic.
    
    TODO: Add inventory reservation
    TODO: Add payment processing integration
    TODO: Add notification events
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
        
        TODO: Implement:
        - Fetch cart items if not provided
        - Validate product availability
        - Reserve inventory
        - Create payment intent
        - Publish order created event
        """
        # Get items from cart or use provided items
        if order_data.items:
            items = order_data.items
        else:
            # TODO: Fetch from cart service
            items = await self._get_cart_items(user_id)
            if not items:
                raise ValueError("Cart is empty")
        
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
        await self.db.refresh(order)
        
        # TODO: Clear cart after order creation
        # TODO: Publish order.created event
        
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
        
        # TODO: Publish order.status_updated event
        # TODO: Send notification to customer
        
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
        
        # TODO: Send shipping notification
        
        return order
    
    async def cancel_order(self, order_id: int, user_id: int) -> Order:
        """
        Cancel an order.
        
        Only allows cancellation if order is pending or confirmed.
        """
        order = await self.get_order(order_id, user_id)
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot cancel order in {order.status.value} status")
        
        order.status = OrderStatus.CANCELLED
        
        # TODO: Release reserved inventory
        # TODO: Process refund if payment was made
        # TODO: Publish order.cancelled event
        
        await self.db.flush()
        await self.db.refresh(order)
        
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
        
        # TODO: Publish order.confirmed event
        
        return order
    
    async def process_payment_failure(self, order_id: int) -> Optional[Order]:
        """Handle failed payment."""
        order = await self.get_order(order_id)
        if not order:
            return None
        
        order.payment_status = PaymentStatus.FAILED
        
        # TODO: Release reserved inventory
        # TODO: Send payment failure notification
        
        await self.db.flush()
        await self.db.refresh(order)
        
        return order
    
    async def _get_cart_items(self, user_id: int) -> list:
        """
        Fetch cart items from cart service.
        
        TODO: Implement cart service integration
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.cart_service_url}/api/v1/cart",
                    headers={"Authorization": f"Bearer user_{user_id}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    cart_items = data.get("data", {}).get("items", [])
                    # Convert to OrderItemCreate format
                    from app.schemas.order import OrderItemCreate
                    return [
                        OrderItemCreate(
                            product_id=item["product_id"],
                            product_name=item["product_name"],
                            product_sku=item["product_sku"],
                            unit_price=Decimal(str(item["unit_price"])),
                            quantity=item["quantity"],
                        )
                        for item in cart_items
                    ]
        except Exception as e:
            print(f"Error fetching cart: {e}")
        return []
