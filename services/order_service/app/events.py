"""
Order Events - RabbitMQ event publishing for order-related events.

Events published:
- order.created: When a new order is placed
- order.confirmed: When payment is successful
- order.status_updated: When order status changes
- order.cancelled: When order is cancelled
- order.shipped: When tracking is added
"""

import json
import logging
from typing import Optional
from decimal import Decimal
from datetime import datetime

import aio_pika
from aio_pika import Message, ExchangeType

from app.config import settings

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class OrderEventPublisher:
    """
    Publishes order events to RabbitMQ for async processing by other services.
    
    Events are published to a topic exchange, allowing consumers to subscribe
    to specific event types using routing keys.
    """
    
    EXCHANGE_NAME = "order_events"
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        self.rabbitmq_url = rabbitmq_url or settings.rabbitmq_url
        self._connection = None
        self._channel = None
        self._exchange = None
    
    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self._connection is None or self._connection.is_closed:
            try:
                self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
                self._channel = await self._connection.channel()
                self._exchange = await self._channel.declare_exchange(
                    self.EXCHANGE_NAME,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                logger.info("Connected to RabbitMQ for order events")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self._connection = None
                raise
    
    async def close(self):
        """Close the RabbitMQ connection."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None
    
    async def publish(self, event_type: str, data: dict):
        """
        Publish an event to RabbitMQ.
        
        Args:
            event_type: Event type (e.g., 'order.created')
            data: Event payload
        """
        try:
            await self.connect()
            
            message = Message(
                body=json.dumps(data, cls=DecimalEncoder).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            
            await self._exchange.publish(message, routing_key=event_type)
            logger.info(f"Published event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            # Don't raise - event publishing should not block order processing
    
    async def publish_order_created(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        total: Decimal,
        items_count: int,
    ):
        """Publish order.created event."""
        await self.publish("order.created", {
            "event": "order.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "user_id": user_id,
                "total": str(total),
                "items_count": items_count,
            }
        })
    
    async def publish_order_confirmed(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        payment_id: str,
    ):
        """Publish order.confirmed event after successful payment."""
        await self.publish("order.confirmed", {
            "event": "order.confirmed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "user_id": user_id,
                "payment_id": payment_id,
            }
        })
    
    async def publish_order_status_updated(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        old_status: str,
        new_status: str,
    ):
        """Publish order.status_updated event."""
        await self.publish("order.status_updated", {
            "event": "order.status_updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "user_id": user_id,
                "old_status": old_status,
                "new_status": new_status,
            }
        })
    
    async def publish_order_cancelled(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        reason: Optional[str] = None,
    ):
        """Publish order.cancelled event."""
        await self.publish("order.cancelled", {
            "event": "order.cancelled",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "user_id": user_id,
                "reason": reason,
            }
        })
    
    async def publish_order_shipped(
        self,
        order_id: int,
        order_number: str,
        user_id: int,
        tracking_number: str,
        carrier: str,
    ):
        """Publish order.shipped event."""
        await self.publish("order.shipped", {
            "event": "order.shipped",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "user_id": user_id,
                "tracking_number": tracking_number,
                "carrier": carrier,
            }
        })


# Singleton instance
event_publisher = OrderEventPublisher()
