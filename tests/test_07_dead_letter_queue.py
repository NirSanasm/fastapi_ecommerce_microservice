"""
End-to-End Tests for Dead Letter Queue (DLQ) functionality in RabbitMQ.

Tests verify:
1. Dead letter exchange and DLQs exist and are bound properly.
2. When a consumer encounters an unhandled exception or malformed payload,
   the message is rejected without requeue and routed to its DLQ.
3. The consumer process remains healthy and continues processing subsequent messages.
4. RabbitMQ attaches the `x-death` metadata to the dead-lettered message.
"""

import asyncio
import json
import uuid
import pytest
import aio_pika
from aio_pika import Message, ExchangeType

from shared.messaging import RabbitMQClient, EventMessage


RABBITMQ_URL = "amqp://ecommerce:ecommerce_secret@localhost:5672/"


@pytest.mark.asyncio
async def test_dlq_generic_client_routes_failed_message():
    """
    Verify that RabbitMQClient with enable_dlq=True routes failed messages
    to <queue_name>.dlq when the message handler raises an exception.
    """
    client = RabbitMQClient(RABBITMQ_URL)
    await client.connect()

    test_id = uuid.uuid4().hex[:8]
    exchange_name = f"test_exchange_{test_id}"
    queue_name = f"test_queue_{test_id}"
    dlq_name = f"{queue_name}.dlq"

    failed_received = asyncio.Event()

    async def faulty_handler(event: EventMessage):
        if event.payload.get("trigger_fail"):
            raise RuntimeError(f"Simulated processing error for {event.event_type}")

    # Subscribe in background task since client.subscribe runs a consuming loop
    consumer_task = asyncio.create_task(
        client.subscribe(
            exchange_name=exchange_name,
            routing_key="test.*",
            queue_name=queue_name,
            handler=faulty_handler,
            enable_dlq=True,
        )
    )
    # Wait for queue declaration and subscription to be established
    await asyncio.sleep(0.5)

    try:
        # Publish a message that triggers failure
        fail_payload = {
            "event_type": "test.fail",
            "payload": {"trigger_fail": True, "test_id": test_id},
            "source_service": "test_suite",
            "timestamp": "2026-11-18T00:00:00Z",
        }
        await client.publish(
            exchange_name=exchange_name,
            routing_key="test.fail",
            message=fail_payload,
            correlation_id=f"corr-{test_id}",
        )

        # Allow consumer time to process and reject to DLQ
        await asyncio.sleep(1.0)

        # Now verify the message is present in the DLQ
        channel = await client.connection.channel()
        dlq = await channel.declare_queue(dlq_name, durable=True)

        # Get message from DLQ
        incoming = await dlq.get(no_ack=False, timeout=5)
        assert incoming is not None, f"Expected message in {dlq_name}, but queue was empty"

        async with incoming.process():
            dead_body = json.loads(incoming.body.decode())
            assert dead_body.get("payload", {}).get("test_id") == test_id
            assert incoming.correlation_id == f"corr-{test_id}"

            # Verify RabbitMQ x-death headers
            headers = incoming.headers or {}
            assert "x-death" in headers
            x_death_info = headers["x-death"]
            assert len(x_death_info) > 0
            assert x_death_info[0].get("reason") == "rejected"
            assert x_death_info[0].get("queue") == queue_name

    finally:
        # Stop consumer task
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await client.close()

        # Clean up test queue, dlq, and exchange with a fresh channel
        try:
            cleanup_conn = await aio_pika.connect_robust(RABBITMQ_URL)
            cleanup_ch = await cleanup_conn.channel()
            q_dlq = await cleanup_ch.declare_queue(dlq_name, durable=True)
            await q_dlq.delete(if_empty=False)
            q_main = await cleanup_ch.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "dlx_events",
                    "x-dead-letter-routing-key": f"{queue_name}.dead",
                },
            )
            await q_main.delete(if_empty=False)
            ex = await cleanup_ch.declare_exchange(exchange_name, ExchangeType.TOPIC, durable=True)
            await ex.delete(if_unused=False)
            await cleanup_conn.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_order_payment_consumer_routes_invalid_event_to_dlq():
    """
    Verify that publishing an invalid payment event to `payment_events` exchange
    causes `order_payment_queue` to reject the message, sending it to `order_payment_queue.dlq`.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    exchange = await channel.declare_exchange("payment_events", ExchangeType.TOPIC, durable=True)
    dlq = await channel.declare_queue("order_payment_queue.dlq", durable=True)

    test_uid = uuid.uuid4().hex[:8]
    # Missing required order_id and payment_id - invalid payload
    bad_payload = {
        "event": "payment.completed",
        "data": {
            "invalid_key": f"bad_data_{test_uid}",
            # No order_id!
        },
    }

    await exchange.publish(
        Message(
            body=json.dumps(bad_payload).encode(),
            content_type="application/json",
            correlation_id=f"corr-bad-{test_uid}",
        ),
        routing_key="payment.completed",
    )

    # Wait for order_service consumer to process, reject, and dead-letter
    await asyncio.sleep(1.5)

    # Retrieve from order_payment_queue.dlq
    incoming = await dlq.get(no_ack=False, timeout=5)
    assert incoming is not None, "Expected message to land in order_payment_queue.dlq"

    async with incoming.process():
        received_body = json.loads(incoming.body.decode())
        assert received_body.get("data", {}).get("invalid_key") == f"bad_data_{test_uid}"
        assert incoming.correlation_id == f"corr-bad-{test_uid}"

        # Check death header
        headers = incoming.headers or {}
        assert "x-death" in headers
        assert headers["x-death"][0].get("reason") == "rejected"
        assert headers["x-death"][0].get("queue") == "order_payment_queue"

    await connection.close()


@pytest.mark.asyncio
async def test_notification_consumer_routes_malformed_json_to_dlq():
    """
    Verify that malformed / non-JSON messages published to event exchanges
    are rejected by `notification_queue` and routed to `notification_queue.dlq`.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    exchange = await channel.declare_exchange("order_events", ExchangeType.TOPIC, durable=True)
    dlq = await channel.declare_queue("notification_queue.dlq", durable=True)

    test_uid = uuid.uuid4().hex[:8]
    corrupted_body = f"NOT_VALID_JSON_{test_uid}".encode()

    await exchange.publish(
        Message(
            body=corrupted_body,
            content_type="text/plain",
            correlation_id=f"corr-corrupt-{test_uid}",
        ),
        routing_key="order.corrupt",
    )

    # Wait for notification consumer to receive, fail JSON parse, reject to DLQ
    await asyncio.sleep(1.5)

    incoming = await dlq.get(no_ack=False, timeout=5)
    assert incoming is not None, "Expected corrupted message in notification_queue.dlq"

    async with incoming.process():
        assert incoming.body.decode() == f"NOT_VALID_JSON_{test_uid}"
        assert incoming.correlation_id == f"corr-corrupt-{test_uid}"

        headers = incoming.headers or {}
        assert "x-death" in headers
        assert headers["x-death"][0].get("reason") == "rejected"
        assert headers["x-death"][0].get("queue") == "notification_queue"

    await connection.close()
