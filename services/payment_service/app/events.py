"""
Payment Events - RabbitMQ event publishing for payment-related events.

Events published:
- payment.completed: When a payment is successfully processed
- payment.failed: When a payment fails
- payment.refunded: When a refund is processed
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


class PaymentEventPublisher:
    """Publishes payment events to RabbitMQ."""
    
    EXCHANGE_NAME = "payment_events"
    
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
                logger.info("Connected to RabbitMQ for payment events")
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
        """Publish an event to RabbitMQ."""
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
    
    async def publish_payment_completed(
        self,
        payment_id: int,
        order_id: int,
        user_id: int,
        amount: Decimal,
        stripe_payment_id: str,
    ):
        """Publish payment.completed event."""
        await self.publish("payment.completed", {
            "event": "payment.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "payment_id": payment_id,
                "order_id": order_id,
                "user_id": user_id,
                "amount": str(amount),
                "stripe_payment_id": stripe_payment_id,
            }
        })
    
    async def publish_payment_failed(
        self,
        payment_id: int,
        order_id: int,
        user_id: int,
        error_message: str,
    ):
        """Publish payment.failed event."""
        await self.publish("payment.failed", {
            "event": "payment.failed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "payment_id": payment_id,
                "order_id": order_id,
                "user_id": user_id,
                "error_message": error_message,
            }
        })
    
    async def publish_payment_refunded(
        self,
        payment_id: int,
        order_id: int,
        user_id: int,
        amount: Decimal,
        order_number: Optional[str] = None,
    ):
        """Publish payment.refunded event."""
        await self.publish("payment.refunded", {
            "event": "payment.refunded",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "payment_id": payment_id,
                "order_id": order_id,
                "user_id": user_id,
                "amount": str(amount),
                "order_number": order_number,
            }
        })


# Singleton instance
event_publisher = PaymentEventPublisher()
