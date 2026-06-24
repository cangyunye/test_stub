import pytest
from mock_server.server import create_app


@pytest.fixture
async def client(aiohttp_client):
    app = create_app()
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_login_page_reachable(client):
    resp = await client.get("/admin/login")
    assert resp.status == 200
    text = await resp.text()
    assert "Mock Server" in text
    assert "登录管理控制台" in text


@pytest.mark.asyncio
async def test_login_failure_wrong_password(client):
    resp = await client.post("/admin/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status == 401
    data = await resp.json()
    assert data["code"] == 401


@pytest.mark.asyncio
async def test_me_unauthorized(client):
    resp = await client.get("/admin/api/auth/me")
    assert resp.status == 401
    data = await resp.json()
    assert data["code"] == 401
