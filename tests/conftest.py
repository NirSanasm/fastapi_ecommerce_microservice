"""
Pytest configuration and shared fixtures for Microservices E2E Test Suite.
"""

import os
import uuid
import pytest
import pytest_asyncio
import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://localhost")


@pytest_asyncio.fixture
async def client():
    """Async HTTP client pointing to the NGINX API Gateway."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def random_user_data():
    """Generate unique user credentials for testing."""
    uid = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{uid}@example.com",
        "password": "SecurePassword123!",
        "first_name": "Test",
        "last_name": f"User{uid}",
        "phone": f"+1555{uuid.uuid4().int % 10000000:07d}",
    }


@pytest_asyncio.fixture
async def registered_user(client: httpx.AsyncClient, random_user_data: dict):
    """Register a new user and return the credentials and registered user object."""
    resp = await client.post("/api/v1/auth/register", json=random_user_data)
    assert resp.status_code in (200, 201), f"Failed to register test user: {resp.text}"
    data = resp.json().get("data", resp.json())
    return {
        "credentials": random_user_data,
        "user": data,
    }


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient, registered_user: dict):
    """Authenticate the registered user and return authorization headers."""
    creds = registered_user["credentials"]
    import asyncio
    resp = None
    for attempt in range(3):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": creds["email"], "password": creds["password"]},
        )
        if resp.status_code == 200:
            break
        await asyncio.sleep(0.2)
        
    assert resp is not None and resp.status_code == 200, f"Login failed for {creds['email']}: {resp.text if resp else 'No response'}"
    token_data = resp.json()
    token = token_data.get("access_token")
    assert token, "Access token missing from login response"
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def authenticated_session(client: httpx.AsyncClient, auth_headers: dict, registered_user: dict):
    """Provide authenticated context with user info."""
    return {
        "client": client,
        "headers": auth_headers,
        "user": registered_user["user"],
        "credentials": registered_user["credentials"],
    }


@pytest_asyncio.fixture
async def available_product(client: httpx.AsyncClient):
    """Retrieve an active product with stock for cart and checkout tests."""
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 200, f"Failed to list products: {resp.text}"
    products = resp.json().get("data", [])
    
    in_stock = [p for p in products if p.get("is_in_stock", True) and p.get("stock_quantity", 0) > 0]
    assert len(in_stock) > 0, "No in-stock products found in the catalog. Ensure catalog has products."
    return in_stock[0]
