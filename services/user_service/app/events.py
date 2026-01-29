"""
User Events - RabbitMQ event publishing for user-related events.

Events published:
- user.registered: When a new user registers
- user.password_reset: When a password reset is requested
"""

import json
import logging
from typing import Optional
from datetime import datetime

import aio_pika
from aio_pika import Message, ExchangeType

from app.config import settings

logger = logging.getLogger(__name__)


class UserEventPublisher:
    """Publishes user events to RabbitMQ."""
    
    EXCHANGE_NAME = "user_events"
    
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
                logger.info("Connected to RabbitMQ for user events")
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
    
    async def publish_user_registered(
        self,
        user_id: int,
        email: str,
        name: str,
    ):
        """Publish user.registered event."""
        await self.publish("user.registered", {
            "event": "user.registered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "user_id": user_id,
                "email": email,
                "name": name,
            }
        })
    
    async def publish_password_reset_requested(
        self,
        user_id: int,
        email: str,
        name: str,
        reset_link: str,
    ):
        """Publish user.password_reset event."""
        await self.publish("user.password_reset", {
            "event": "user.password_reset",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "user_id": user_id,
                "email": email,
                "name": name,
                "reset_link": reset_link,
            }
        })


# Singleton instance
event_publisher = UserEventPublisher()
