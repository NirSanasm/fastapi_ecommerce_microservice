"""
Tests for User Service authentication, registration, JWT lifecycle, and profiles.
"""

import uuid
import pytest
import httpx


@pytest.mark.asyncio
async def test_user_registration_success(client: httpx.AsyncClient, random_user_data: dict):
    """Verify new customer registration."""
    response = await client.post("/api/v1/auth/register", json=random_user_data)
    assert response.status_code == 201
    result = response.json()
    assert result["success"] is True
    data = result["data"]
    assert data["email"] == random_user_data["email"].lower()
    assert data["role"] == "customer"
    assert "id" in data


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(client: httpx.AsyncClient, registered_user: dict):
    """Verify that registering with an existing email fails."""
    creds = registered_user["credentials"]
    response = await client.post("/api/v1/auth/register", json=creds)
    assert response.status_code == 400
    assert "already registered" in response.text.lower() or "exists" in response.text.lower()


@pytest.mark.asyncio
async def test_user_login_success(client: httpx.AsyncClient, registered_user: dict):
    """Verify user login returns access and refresh tokens."""
    creds = registered_user["credentials"]
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_user_login_invalid_password(client: httpx.AsyncClient, registered_user: dict):
    """Verify login rejection with incorrect credentials."""
    creds = registered_user["credentials"]
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": creds["email"], "password": "WrongPassword123!"},
    )
    assert response.status_code in (400, 401)


@pytest.mark.asyncio
async def test_profile_unauthorized(client: httpx.AsyncClient):
    """Verify protected endpoints reject requests without a token."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_authenticated(authenticated_session: dict):
    """Verify retrieving current user profile with valid Bearer token."""
    client = authenticated_session["client"]
    headers = authenticated_session["headers"]
    expected_email = authenticated_session["credentials"]["email"]

    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["email"].lower() == expected_email.lower()


@pytest.mark.asyncio
async def test_update_profile(authenticated_session: dict):
    """Verify updating user profile information."""
    client = authenticated_session["client"]
    headers = authenticated_session["headers"]

    update_payload = {
        "first_name": "UpdatedName",
        "last_name": "UpdatedLast",
        "phone": "+19998887777",
    }
    response = await client.put("/api/v1/users/me", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["first_name"] == "UpdatedName"
    assert data["last_name"] == "UpdatedLast"


@pytest.mark.asyncio
async def test_refresh_token(client: httpx.AsyncClient, registered_user: dict):
    """Verify refreshing access token using valid refresh token."""
    creds = registered_user["credentials"]
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens

