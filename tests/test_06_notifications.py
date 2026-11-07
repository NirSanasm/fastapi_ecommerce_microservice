"""
Tests for Notification Service templates and notification endpoints.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_notification_templates(client: httpx.AsyncClient):
    """Verify listing available notification email templates."""
    response = await client.get("/api/v1/notifications/templates")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data.get("success") is True
    data = res_data.get("data", {})
    templates = data.get("templates", data) if isinstance(data, dict) else data
    assert isinstance(templates, list)
    assert "order_confirmation" in templates
    assert "order_shipped" in templates
    assert "welcome" in templates
