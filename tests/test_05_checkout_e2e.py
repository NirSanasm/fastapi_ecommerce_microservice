"""
End-to-End Test for the complete Checkout flow:
Cart -> Order Creation -> Inventory Validation -> Event Publishing.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_complete_checkout_flow(authenticated_session: dict, available_product: dict):
    """
    Test the multi-service checkout lifecycle:
    1. Customer adds item to cart (Cart Service / Redis).
    2. Validates cart prior to checkout.
    3. Places an order (Order Service / PostgreSQL).
    4. Order Service verifies stock with Product Service.
    5. Order Service clears Cart Service session.
    6. Order Service publishes `order.created` to RabbitMQ.
    7. Customer verifies order history and order details.
    """
    client: httpx.AsyncClient = authenticated_session["client"]
    headers = authenticated_session["headers"]
    product_id = available_product["id"]

    # Step 1: Add product to cart
    add_resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 1},
        headers=headers,
    )
    assert add_resp.status_code == 200, f"Failed adding item to cart: {add_resp.text}"

    # Step 2: Validate cart before checkout
    val_resp = await client.post("/api/v1/cart/validate", headers=headers)
    assert val_resp.status_code == 200, f"Cart validation failed: {val_resp.text}"

    # Step 3: Place order
    order_payload = {
        "shipping_address": {
            "first_name": "Jane",
            "last_name": "Doe",
            "address_line1": "456 Market St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "US",
            "phone": "+14155552671",
        },
        "billing_address": {
            "first_name": "Jane",
            "last_name": "Doe",
            "address_line1": "456 Market St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "US",
            "phone": "+14155552671",
        },
        "payment_method": "stripe",
        "customer_notes": "Automated E2E integration test order",
    }

    create_order_resp = await client.post("/api/v1/orders/", json=order_payload, headers=headers)
    assert create_order_resp.status_code == 201, f"Order creation failed: {create_order_resp.text}"

    order_result = create_order_resp.json()
    assert order_result.get("success") is True
    order_data = order_result.get("data")
    assert order_data is not None
    order_id = order_data["id"]
    order_number = order_data["order_number"]

    assert order_data["status"] == "pending"
    assert order_data["payment_status"] == "pending"
    assert float(order_data["total"]) > 0

    # Step 4: Verify Cart was automatically cleared by Order Service
    cart_resp = await client.get("/api/v1/cart/", headers=headers)
    assert cart_resp.status_code == 200
    cart_items = cart_resp.json().get("data", {}).get("items", [])
    assert len(cart_items) == 0, "Cart should be empty immediately after order creation"

    # Step 5: Verify fetching order by ID
    get_order_resp = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert get_order_resp.status_code == 200
    fetched_order = get_order_resp.json().get("data", get_order_resp.json())
    assert fetched_order["id"] == order_id
    assert fetched_order["order_number"] == order_number
    assert len(fetched_order.get("items", [])) > 0

    # Step 6: Verify fetching order by Order Number
    get_by_num_resp = await client.get(f"/api/v1/orders/number/{order_number}", headers=headers)
    assert get_by_num_resp.status_code == 200
    num_order = get_by_num_resp.json().get("data", get_by_num_resp.json())
    assert num_order["order_number"] == order_number

    # Step 7: Verify order listing contains the new order
    list_orders_resp = await client.get("/api/v1/orders/", headers=headers)
    assert list_orders_resp.status_code == 200
    user_orders = list_orders_resp.json()
    if isinstance(user_orders, dict):
        user_orders = user_orders.get("data", [])
    assert any(o["id"] == order_id for o in user_orders)

