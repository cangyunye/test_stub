import pytest
from mock_server.server import create_app


@pytest.fixture
async def client(aiohttp_client):
    app = create_app()
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_unmatched_route_returns_404(client):
    resp = await client.get("/nonexistent")
    assert resp.status == 404
    data = await resp.json()
    assert data["error"] == "not found"
