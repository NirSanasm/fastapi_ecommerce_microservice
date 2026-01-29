"""
Event Consumer - RabbitMQ consumer for notification events.

Subscribes to:
- order.* events (order.created, order.confirmed, order.shipped, order.cancelled)
- user.* events (user.registered, user.password_reset)
- inventory.* events (inventory.low_stock, inventory.out_of_stock)
- payment.* events (payment.refunded)
"""

import asyncio
import json
import logging
from typing import Optional

import aio_pika
from aio_pika import Message, ExchangeType, IncomingMessage
import httpx

from app.config import settings
from app.services.email_service import EmailService
from app.schemas.notification import NotificationType

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    RabbitMQ consumer for notification-triggering events.
    
    Listens to multiple exchanges and processes events to send notifications.
    """
    
    EXCHANGES = ["order_events", "user_events", "product_events", "payment_events"]
    QUEUE_NAME = "notification_queue"
    
    def __init__(self):
        self.rabbitmq_url = settings.rabbitmq_url
        self._connection = None
        self._channel = None
        self._queue = None
        self.email_service = EmailService()
        self._running = False
    
    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)
            
            # Declare queue
            self._queue = await self._channel.declare_queue(
                self.QUEUE_NAME,
                durable=True,
            )
            
            # Bind to all exchanges
            for exchange_name in self.EXCHANGES:
                exchange = await self._channel.declare_exchange(
                    exchange_name,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                # Bind with wildcard to receive all events from each exchange
                await self._queue.bind(exchange, routing_key="#")
            
            logger.info("Connected to RabbitMQ and bound to all event exchanges")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    async def start(self):
        """Start consuming events."""
        if not await self.connect():
            logger.warning("Could not connect to RabbitMQ. Events will not be processed.")
            return
        
        self._running = True
        logger.info("Starting event consumer...")
        
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break
                async with message.process():
                    await self._handle_message(message)
    
    async def stop(self):
        """Stop the consumer and close connection."""
        self._running = False
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("Event consumer stopped")
    
    async def _handle_message(self, message: IncomingMessage):
        """Process an incoming message."""
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event", "unknown")
            data = body.get("data", {})
            
            logger.info(f"Processing event: {event_type}")
            
            # Route to appropriate handler
            if event_type.startswith("order."):
                await self._handle_order_event(event_type, data)
            elif event_type.startswith("user."):
                await self._handle_user_event(event_type, data)
            elif event_type.startswith("inventory."):
                await self._handle_inventory_event(event_type, data)
            elif event_type.startswith("payment."):
                await self._handle_payment_event(event_type, data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message: {message.body}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_order_event(self, event_type: str, data: dict):
        """Handle order-related events."""
        order_id = data.get("order_id")
        order_number = data.get("order_number", "")
        user_id = data.get("user_id")
        
        # Fetch user details
        user = await self._get_user(user_id)
        if not user:
            logger.warning(f"Could not fetch user {user_id} for order event")
            return
        
        email = user.get("email")
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Customer"
        
        if event_type == "order.created":
            await self.email_service.send_order_notification(
                order_id=order_id,
                order_number=order_number,
                customer_email=email,
                customer_name=name,
                notification_type=NotificationType.ORDER_CONFIRMATION,
                order_data={"total": data.get("total", "0")},
            )
            logger.info(f"Sent order confirmation email for order {order_number}")
            
        elif event_type == "order.shipped":
            await self.email_service.send_order_notification(
                order_id=order_id,
                order_number=order_number,
                customer_email=email,
                customer_name=name,
                notification_type=NotificationType.ORDER_SHIPPED,
                order_data={
                    "tracking_number": data.get("tracking_number", ""),
                    "carrier": data.get("carrier", ""),
                },
            )
            logger.info(f"Sent shipping notification for order {order_number}")
            
        elif event_type == "order.confirmed":
            # Payment successful - could send a separate confirmation
            logger.info(f"Order {order_number} confirmed (payment successful)")
            
        elif event_type == "order.cancelled":
            await self.email_service.send_email(
                to_email=email,
                to_name=name,
                subject=f"Order Cancelled - #{order_number}",
                body_html=f"""
                    <h1>Order Cancelled</h1>
                    <p>Hi {name},</p>
                    <p>Your order #{order_number} has been cancelled.</p>
                    <p>Reason: {data.get('reason', 'Customer requested cancellation')}</p>
                """,
            )
            logger.info(f"Sent cancellation email for order {order_number}")
    
    async def _handle_user_event(self, event_type: str, data: dict):
        """Handle user-related events."""
        email = data.get("email")
        name = data.get("name", "Customer")
        
        if event_type == "user.registered":
            await self.email_service.send_email(
                to_email=email,
                to_name=name,
                subject="Welcome to our store!",
                template_name="welcome",
                template_data={"customer_name": name},
            )
            logger.info(f"Sent welcome email to {email}")
            
        elif event_type == "user.password_reset":
            reset_link = data.get("reset_link", "#")
            await self.email_service.send_email(
                to_email=email,
                to_name=name,
                subject="Password Reset Request",
                template_name="password_reset",
                template_data={"reset_link": reset_link},
            )
            logger.info(f"Sent password reset email to {email}")
    
    async def _handle_inventory_event(self, event_type: str, data: dict):
        """Handle inventory-related events (admin alerts)."""
        product_id = data.get("product_id")
        product_name = data.get("product_name", f"Product {product_id}")
        stock_quantity = data.get("stock_quantity", 0)
        
        # Send to admin email (could be configurable)
        admin_email = settings.brevo_from_email
        
        if event_type == "inventory.low_stock":
            await self.email_service.send_email(
                to_email=admin_email,
                subject=f"Low Stock Alert: {product_name}",
                body_html=f"""
                    <h1>Low Stock Alert</h1>
                    <p>Product: {product_name} (ID: {product_id})</p>
                    <p>Current stock: {stock_quantity}</p>
                    <p>Please reorder soon.</p>
                """,
            )
            logger.info(f"Sent low stock alert for {product_name}")
            
        elif event_type == "inventory.out_of_stock":
            await self.email_service.send_email(
                to_email=admin_email,
                subject=f"OUT OF STOCK: {product_name}",
                body_html=f"""
                    <h1>Out of Stock Alert</h1>
                    <p>Product: {product_name} (ID: {product_id})</p>
                    <p>This product is now out of stock!</p>
                """,
            )
            logger.info(f"Sent out of stock alert for {product_name}")
    
    async def _handle_payment_event(self, event_type: str, data: dict):
        """Handle payment-related events."""
        if event_type == "payment.refunded":
            user_id = data.get("user_id")
            user = await self._get_user(user_id)
            if not user:
                return
            
            await self.email_service.send_email(
                to_email=user.get("email"),
                to_name=f"{user.get('first_name', '')} {user.get('last_name', '')}",
                subject="Refund Processed",
                body_html=f"""
                    <h1>Refund Confirmation</h1>
                    <p>Your refund of ${data.get('amount', '0')} has been processed.</p>
                    <p>Order: #{data.get('order_number', 'N/A')}</p>
                """,
            )
            logger.info(f"Sent refund confirmation email")
    
    async def _get_user(self, user_id: int) -> Optional[dict]:
        """Fetch user details from user service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.user_service_url}/api/v1/users/{user_id}",
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", data)
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
        return None


# Singleton instance
event_consumer = EventConsumer()
