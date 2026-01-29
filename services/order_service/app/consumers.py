"""
Order Event Consumer - RabbitMQ consumer for payment events.

Listens for:
- payment.completed: Update order status to confirmed
- payment.failed: Mark order for payment retry/cancellation
"""

import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType, IncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import db_manager

logger = logging.getLogger(__name__)


class PaymentEventConsumer:
    """
    RabbitMQ consumer for payment events.
    
    Listens to payment_events exchange and updates order status accordingly.
    """
    
    EXCHANGE_NAME = "payment_events"
    QUEUE_NAME = "order_payment_queue"
    
    def __init__(self):
        self.rabbitmq_url = settings.rabbitmq_url
        self._connection = None
        self._channel = None
        self._queue = None
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
            
            # Bind to payment_events exchange
            exchange = await self._channel.declare_exchange(
                self.EXCHANGE_NAME,
                ExchangeType.TOPIC,
                durable=True,
            )
            
            # Listen for payment.completed and payment.failed
            await self._queue.bind(exchange, routing_key="payment.completed")
            await self._queue.bind(exchange, routing_key="payment.failed")
            
            logger.info("Connected to RabbitMQ for payment event consumption")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    async def start(self):
        """Start consuming events."""
        if not await self.connect():
            logger.warning("Could not connect to RabbitMQ. Payment events will not be processed.")
            return
        
        self._running = True
        logger.info("Starting payment event consumer...")
        
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
        logger.info("Payment event consumer stopped")
    
    async def _handle_message(self, message: IncomingMessage):
        """Process an incoming payment event."""
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event", "unknown")
            data = body.get("data", {})
            
            logger.info(f"Processing payment event: {event_type}")
            
            async with db_manager.async_session() as db:
                if event_type == "payment.completed":
                    await self._handle_payment_completed(db, data)
                elif event_type == "payment.failed":
                    await self._handle_payment_failed(db, data)
                
                await db.commit()
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message: {message.body}")
        except Exception as e:
            logger.error(f"Error processing payment event: {e}")
    
    async def _handle_payment_completed(self, db: AsyncSession, data: dict):
        """Handle successful payment - confirm order."""
        from app.services.order_service import OrderService
        
        order_id = data.get("order_id")
        payment_id = str(data.get("payment_id"))
        
        if not order_id:
            logger.warning("Payment completed event missing order_id")
            return
        
        order_service = OrderService(db)
        order = await order_service.process_payment_success(order_id, payment_id)
        
        if order:
            logger.info(f"Order {order.order_number} confirmed after payment")
        else:
            logger.warning(f"Order {order_id} not found for payment confirmation")
    
    async def _handle_payment_failed(self, db: AsyncSession, data: dict):
        """Handle failed payment."""
        from app.services.order_service import OrderService
        
        order_id = data.get("order_id")
        
        if not order_id:
            logger.warning("Payment failed event missing order_id")
            return
        
        order_service = OrderService(db)
        order = await order_service.process_payment_failure(order_id)
        
        if order:
            logger.info(f"Order {order.order_number} marked with payment failure")
        else:
            logger.warning(f"Order {order_id} not found for payment failure handling")


# Singleton instance
payment_consumer = PaymentEventConsumer()
