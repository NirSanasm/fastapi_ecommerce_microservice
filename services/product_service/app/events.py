"""
Product Events - RabbitMQ event publishing for product/inventory events.

Events published:
- inventory.low_stock: When stock falls below threshold
- inventory.out_of_stock: When stock reaches 0
- product.created: When a new product is added
"""

import json
import logging
from typing import Optional
from datetime import datetime

import aio_pika
from aio_pika import Message, ExchangeType

from app.config import settings

logger = logging.getLogger(__name__)


class ProductEventPublisher:
    """Publishes product/inventory events to RabbitMQ."""
    
    EXCHANGE_NAME = "product_events"
    
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
                logger.info("Connected to RabbitMQ for product events")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self._connection = None
                raise
    
    async def publish(self, event_type: str, data: dict):
        """Publish an event to RabbitMQ."""
        try:
            await self.connect()
            
            message = Message(
                body=json.dumps(data).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            
            await self._exchange.publish(message, routing_key=event_type)
            logger.info(f"Published event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
    
    async def publish_low_stock(
        self,
        product_id: int,
        product_name: str,
        stock_quantity: int,
    ):
        """Publish inventory.low_stock event."""
        await self.publish("inventory.low_stock", {
            "event": "inventory.low_stock",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "product_id": product_id,
                "product_name": product_name,
                "stock_quantity": stock_quantity,
            }
        })
    
    async def publish_out_of_stock(
        self,
        product_id: int,
        product_name: str,
    ):
        """Publish inventory.out_of_stock event."""
        await self.publish("inventory.out_of_stock", {
            "event": "inventory.out_of_stock",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "product_id": product_id,
                "product_name": product_name,
                "stock_quantity": 0,
            }
        })
    
    async def publish_product_created(
        self,
        product_id: int,
        product_name: str,
        sku: str,
    ):
        """Publish product.created event."""
        await self.publish("product.created", {
            "event": "product.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "product_id": product_id,
                "product_name": product_name,
                "sku": sku,
            }
        })


# Singleton instance
event_publisher = ProductEventPublisher()
