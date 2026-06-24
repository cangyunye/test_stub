import pytest
from mock_server.server import create_app
from mock_server.auth import create_session


@pytest.fixture
async def client(aiohttp_client):
    app = create_app()
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_admin_dashboard_redirects_to_login_when_unauthorized(client):
    # 未认证时 /admin/ 应被中间件重定向到登录页
    resp = await client.get("/admin/", allow_redirects=False)
    assert resp.status == 302
    assert "/admin/login" in resp.headers.get("Location", "")


@pytest.mark.asyncio
async def test_admin_login_page_reachable(client):
    resp = await client.get("/admin/login")
    assert resp.status == 200
    text = await resp.text()
    assert "Mock Server" in text
    assert "登录管理控制台" in text


@pytest.mark.asyncio
async def test_admin_dashboard_with_auth(client):
    session_id = create_session(
        {"id": 1, "username": "admin", "display_name": "Admin", "is_superuser": True},
        ["*"]
    )
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})

    resp = await client.get("/admin/index.html")
    assert resp.status == 200
    text = await resp.text()
    assert "仪表盘" in text


@pytest.mark.asyncio
async def test_admin_endpoints_page_with_auth(client):
    session_id = create_session(
        {"id": 1, "username": "admin", "display_name": "Admin", "is_superuser": True},
        ["*"]
    )
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})

    resp = await client.get("/admin/endpoints.html")
    assert resp.status == 200
    text = await resp.text()
    assert "端点管理" in text


@pytest.mark.asyncio
async def test_admin_logs_page_with_auth(client):
    session_id = create_session(
        {"id": 1, "username": "admin", "display_name": "Admin", "is_superuser": True},
        ["*"]
    )
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})

    resp = await client.get("/admin/logs.html")
    assert resp.status == 200
    text = await resp.text()
    assert "请求日志" in text


@pytest.mark.asyncio
async def test_admin_users_page_with_auth(client):
    session_id = create_session(
        {"id": 1, "username": "admin", "display_name": "Admin", "is_superuser": True},
        ["*"]
    )
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})

    resp = await client.get("/admin/users.html")
    assert resp.status == 200
    text = await resp.text()
    assert "用户与权限" in text


@pytest.mark.asyncio
async def test_dashboard_stats_api_with_auth(client):
    session_id = create_session(
        {"id": 1, "username": "admin", "display_name": "Admin", "is_superuser": True},
        ["*"]
    )
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})

    resp = await client.get("/admin/api/dashboard/stats")
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 200
    assert "endpoint_count" in data["data"]