"""
Tests for Product Service catalog, categories, search, and stock queries.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_categories(client: httpx.AsyncClient):
    """Verify category listing."""
    response = await client.get("/api/v1/categories/")
    assert response.status_code == 200
    res_data = response.json()
    assert "data" in res_data
    assert isinstance(res_data["data"], list)


@pytest.mark.asyncio
async def test_list_products(client: httpx.AsyncClient):
    """Verify catalog product listing and response schema."""
    response = await client.get("/api/v1/products/")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data.get("success") is True
    products = res_data.get("data", [])
    assert isinstance(products, list)
    assert len(products) > 0, "Expected at least one product in catalog."

    first_product = products[0]
    assert "id" in first_product
    assert "name" in first_product
    assert "price" in first_product
    assert "stock_quantity" in first_product


@pytest.mark.asyncio
async def test_get_product_by_id(client: httpx.AsyncClient, available_product: dict):
    """Verify fetching specific product details by ID."""
    product_id = available_product["id"]
    response = await client.get(f"/api/v1/products/{product_id}")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["id"] == product_id
    assert data["name"] == available_product["name"]


@pytest.mark.asyncio
async def test_product_stock_query(client: httpx.AsyncClient, available_product: dict):
    """Verify querying inventory stock for a product."""
    product_id = available_product["id"]
    response = await client.get(f"/api/v1/products/{product_id}/stock")
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert "stock_quantity" in data
    assert data["stock_quantity"] >= 0


@pytest.mark.asyncio
async def test_product_not_found(client: httpx.AsyncClient):
    """Verify 404 response for non-existent product."""
    response = await client.get("/api/v1/products/99999999")
    assert response.status_code == 404

