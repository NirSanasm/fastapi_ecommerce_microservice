"""
RabbitMQ async messaging client for inter-service communication.
Provides publish/subscribe functionality for event-driven architecture.
"""

import json
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass
import aio_pika
from aio_pika import Message, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange


@dataclass
class EventMessage:
    """Event message structure."""
    event_type: str
    payload: dict
    source_service: str
    timestamp: str
    correlation_id: Optional[str] = None


class RabbitMQClient:
    """
    Async RabbitMQ client for publishing and consuming messages.
    
    Usage:
        # Publisher
        client = RabbitMQClient(rabbitmq_url)
        await client.connect()
        await client.publish("orders", {"event": "order_created", "order_id": 123})
        
        # Consumer
        async def handler(message: EventMessage):
            print(f"Received: {message.event_type}")
        
        await client.subscribe("orders", handler)
    """
    
    def __init__(self, url: str = "amqp://guest:guest@localhost:5672/"):
        """
        Initialize RabbitMQ client.
        
        Args:
            url: RabbitMQ connection URL
        """
        self.url = url
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchanges: dict[str, AbstractExchange] = {}
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
    
    async def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
    
    async def _get_exchange(self, exchange_name: str) -> AbstractExchange:
        """Get or create an exchange."""
        if exchange_name not in self.exchanges:
            self.exchanges[exchange_name] = await self.channel.declare_exchange(
                exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )
        return self.exchanges[exchange_name]
    
    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: dict,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Publish a message to an exchange.
        
        Args:
            exchange_name: Name of the exchange
            routing_key: Routing key for the message
            message: Message payload (dict)
            correlation_id: Optional correlation ID for tracking
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        exchange = await self._get_exchange(exchange_name)
        
        message_body = json.dumps(message).encode()
        
        await exchange.publish(
            Message(
                body=message_body,
                content_type="application/json",
                correlation_id=correlation_id,
            ),
            routing_key=routing_key,
        )
    
    async def subscribe(
        self,
        exchange_name: str,
        routing_key: str,
        queue_name: str,
        handler: Callable[[EventMessage], Any],
    ) -> None:
        """
        Subscribe to messages from an exchange.
        
        Args:
            exchange_name: Name of the exchange
            routing_key: Routing key pattern (can use wildcards)
            queue_name: Name of the queue to create
            handler: Async function to handle messages
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        exchange = await self._get_exchange(exchange_name)
        
        # Declare queue
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True,
        )
        
        # Bind queue to exchange
        await queue.bind(exchange, routing_key=routing_key)
        
        # Start consuming
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        event = EventMessage(
                            event_type=body.get("event_type", "unknown"),
                            payload=body.get("payload", body),
                            source_service=body.get("source_service", "unknown"),
                            timestamp=body.get("timestamp", ""),
                            correlation_id=message.correlation_id,
                        )
                        await handler(event)
                    except Exception as e:
                        # TODO: Implement dead letter queue for failed messages
                        print(f"Error processing message: {e}")


# Event types for the platform
class EventTypes:
    """Standard event types for the e-commerce platform."""
    
    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_CONFIRMED = "order.confirmed"
    ORDER_SHIPPED = "order.shipped"
    ORDER_DELIVERED = "order.delivered"
    ORDER_CANCELLED = "order.cancelled"
    
    # Payment events
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    
    # Inventory events
    INVENTORY_LOW = "inventory.low"
    INVENTORY_OUT_OF_STOCK = "inventory.out_of_stock"
    INVENTORY_RESTOCKED = "inventory.restocked"


# Helper function to create event message
def create_event(
    event_type: str,
    payload: dict,
    source_service: str,
) -> dict:
    """
    Create a standardized event message.
    
    Args:
        event_type: Type of event (use EventTypes constants)
        payload: Event data
        source_service: Name of the service sending the event
        
    Returns:
        Dict formatted for publishing
    """
    from datetime import datetime
    
    return {
        "event_type": event_type,
        "payload": payload,
        "source_service": source_service,
        "timestamp": datetime.utcnow().isoformat(),
    }
