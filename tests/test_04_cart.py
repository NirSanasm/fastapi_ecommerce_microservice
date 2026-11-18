"""
Tests for Cart Service (Redis session and authenticated user cart operations).
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_authenticated_cart_flow(authenticated_session: dict, available_product: dict):
    """Verify full cart lifecycle for an authenticated user."""
    client: httpx.AsyncClient = authenticated_session["client"]
    headers = authenticated_session["headers"]
    product_id = available_product["id"]

    # 1. Clear cart to start clean
    await client.delete("/api/v1/cart/", headers=headers)

    # 2. Add product to cart
    add_resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 2},
        headers=headers,
    )
    assert add_resp.status_code == 200
    cart_data = add_resp.json().get("data", add_resp.json())
    assert cart_data.get("total_items", 0) >= 2 or len(cart_data.get("items", [])) > 0

    # 3. View cart
    get_resp = await client.get("/api/v1/cart/", headers=headers)
    assert get_resp.status_code == 200
    current_cart = get_resp.json().get("data", get_resp.json())
    items = current_cart.get("items", [])
    item_matches = [i for i in items if i["product_id"] == product_id]
    assert len(item_matches) == 1
    assert item_matches[0]["quantity"] == 2

    # 4. Update quantity
    update_resp = await client.put(
        f"/api/v1/cart/items/{product_id}",
        json={"quantity": 3},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated_cart = update_resp.json().get("data", update_resp.json())
    updated_item = [i for i in updated_cart.get("items", []) if i["product_id"] == product_id][0]
    assert updated_item["quantity"] == 3

    # 5. Check cart summary
    summary_resp = await client.get("/api/v1/cart/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json().get("data", summary_resp.json())
    assert "subtotal" in summary
    assert "total" in summary
    assert summary.get("item_count") == 3

    # 6. Remove item from cart
    delete_item_resp = await client.delete(f"/api/v1/cart/items/{product_id}", headers=headers)
    assert delete_item_resp.status_code == 200

    # 7. Verify cart is empty
    empty_cart_resp = await client.get("/api/v1/cart/", headers=headers)
    empty_items = empty_cart_resp.json().get("data", {}).get("items", [])
    assert len(empty_items) == 0


@pytest.mark.asyncio
async def test_validate_cart_checkout(authenticated_session: dict, available_product: dict):
    """Verify that cart validation succeeds for in-stock items."""
    client: httpx.AsyncClient = authenticated_session["client"]
    headers = authenticated_session["headers"]

    # 1. Clean cart
    await client.delete("/api/v1/cart/", headers=headers)

    # 2. Add in-stock product
    await client.post(
        "/api/v1/cart/items",
        json={"product_id": available_product["id"], "quantity": 1},
        headers=headers,
    )

    # 3. Validation step
    response = await client.post("/api/v1/cart/validate", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data.get("success") is True
    validation_details = res_data.get("data", {})
    assert validation_details.get("is_valid") is True


@pytest.mark.asyncio
async def test_guest_cart_and_merge_flow(client: httpx.AsyncClient, authenticated_session: dict, available_product: dict):
    """Verify guest cart operations and merging guest cart into authenticated user cart upon login."""
    auth_headers = authenticated_session["headers"]
    product_id = available_product["id"]
    guest_id = "guest_test_merge_99"
    guest_headers = {"X-Guest-ID": guest_id}

    # 1. Clean both guest and auth carts
    await client.delete("/api/v1/cart/", headers=guest_headers)
    await client.delete("/api/v1/cart/", headers=auth_headers)

    # 2. Add product as guest
    guest_add_resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 2},
        headers=guest_headers,
    )
    assert guest_add_resp.status_code == 200
    guest_cart = guest_add_resp.json().get("data", {})
    assert len(guest_cart.get("items", [])) == 1
    assert guest_cart["items"][0]["quantity"] == 2

    # 3. Add 1 item to user cart prior to merge
    await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 1},
        headers=auth_headers,
    )

    # 4. Merge guest cart into authenticated cart
    merge_resp = await client.post(
        "/api/v1/cart/merge",
        json={"guest_cart_id": guest_id},
        headers=auth_headers,
    )
    assert merge_resp.status_code == 200
    merged_data = merge_resp.json().get("data", {})
    merged_items = merged_data.get("items", [])
    assert len(merged_items) == 1
    # 2 from guest + 1 from user = 3
    assert merged_items[0]["quantity"] == 3

    # 5. Verify guest cart is cleared in Redis
    guest_check = await client.get("/api/v1/cart/", headers=guest_headers)
    assert guest_check.status_code == 200
    assert len(guest_check.json().get("data", {}).get("items", [])) == 0
