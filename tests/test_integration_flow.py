"""端到端集成测试：用户创建 → 端点创建 → 公共/归属端点调用"""
import pytest
from aiohttp import web
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from mock_server.db import AsyncSessionLocal, init_db
from mock_server.models import User, Role, Endpoint, UserRole
from mock_server.server import create_app


@pytest.fixture
async def app():
    await init_db()
    app = create_app()
    return app


@pytest.fixture
async def client(aiohttp_client, app):
    return await aiohttp_client(app)


async def _login(client) -> str:
    """Login as admin, return session cookie value."""
    resp = await client.post("/admin/api/auth/login", json={
        "username": "admin", "password": "admin123",
    })
    assert resp.status == 200
    cookies = resp.headers.getall("Set-Cookie", [])
    for c in cookies:
        if c.startswith("mock_session_id="):
            return c.split(";")[0].split("=", 1)[1]
    raise AssertionError("No session cookie in response")


async def _set_cookie(client, session_id: str):
    client.session.cookie_jar.clear()
    client.session.cookie_jar.update_cookies({"mock_session_id": session_id})


class TestIntegrationFlow:

    @pytest.mark.asyncio
    async def test_01_create_user_with_role(self, client):
        """创建用户并分配角色，验证角色关联正确"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Create user
        resp = await client.post("/admin/api/users", json={
            "username": "dev1",
            "password": "pass123",
            "display_name": "Developer",
            "role_ids": [2],
        })
        body = await resp.json()
        assert body["code"] == 201, body
        user_id = body["data"]["id"]

        # Verify user in DB with role
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id).options(selectinload(User.roles))
            user = (await session.execute(stmt)).scalar_one()
            assert user.username == "dev1"
            assert len(user.roles) == 1
            assert user.roles[0].id == 2

    @pytest.mark.asyncio
    async def test_02_create_user_without_role(self, client):
        """创建用户不分配角色，验证角色列表为空"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.post("/admin/api/users", json={
            "username": "nobody",
            "password": "pass123",
            "display_name": "No Role",
        })
        body = await resp.json()
        assert body["code"] == 201, body

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.username == "nobody").options(selectinload(User.roles))
            user = (await session.execute(stmt)).scalar_one()
            assert len(user.roles) == 0

    @pytest.mark.asyncio
    async def test_03_user_list_shows_roles(self, client):
        """用户列表 API 返回角色信息"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.get("/admin/api/users?page=1&page_size=100")
        body = await resp.json()
        assert body["code"] == 200
        items = body["data"]["items"]
        assert len(items) >= 2

        for u in items:
            assert "roles" in u
            assert isinstance(u["roles"], list)

    @pytest.mark.asyncio
    async def test_04_create_public_endpoint(self, client):
        """创建公共端点，无需 stub-x-token 即可访问"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET",
            "path": "/api/public-test",
            "status_code": 200,
            "response_body": '{"ok": true, "msg": "public"}',
            "owner_id": None,
            "is_active": True,
        })
        body = await resp.json()
        assert body["code"] == 201, body

        # Access without token — should succeed
        resp = await client.get("/api/public-test")
        assert resp.status == 200
        data = await resp.json()
        assert data["msg"] == "public"

    @pytest.mark.asyncio
    async def test_05_create_owned_endpoint(self, client):
        """创建归属端点为 admin (owner_id=1)，验证无 token 404，有 token 200"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET",
            "path": "/api/owner-test",
            "status_code": 200,
            "response_body": '{"ok": true, "msg": "owner only"}',
            "owner_id": 1,
            "is_active": True,
        })
        body = await resp.json()
        assert body["code"] == 201, body

        # Access without token — should 404
        resp = await client.get("/api/owner-test")
        assert resp.status == 404

        # Access WITH token — should succeed
        resp = await client.get("/api/owner-test", headers={"stub-x-token": "admin"})
        assert resp.status == 200
        data = await resp.json()
        assert data["msg"] == "owner only"

    @pytest.mark.asyncio
    async def test_06_edit_endpoint_preserves_owner(self, client):
        """编辑端点后归属用户不变"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        async with AsyncSessionLocal() as session:
            stmt = select(Endpoint).where(Endpoint.path == "/api/owner-test")
            ep = (await session.execute(stmt)).scalar_one()

        resp = await client.put(f"/admin/api/endpoints/{ep.id}", json={
            "method": "GET",
            "path": "/api/owner-test",
            "status_code": 200,
            "response_body": '{"updated": true}',
            "owner_id": 1,
        })
        body = await resp.json()
        assert body["code"] == 200

        # Verify owner_id preserved
        async with AsyncSessionLocal() as session:
            ep = await session.get(Endpoint, ep.id)
            assert ep.owner_id == 1

    @pytest.mark.asyncio
    async def test_07_edit_endpoint_change_owner(self, client):
        """编辑端点时修改归属用户"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Create a second user via API to assign as owner
        resp = await client.post("/admin/api/users", json={
            "username": "owneruser",
            "password": "pass123",
            "display_name": "Owner User",
            "role_ids": [],
        })
        body = await resp.json()
        new_user_id = body["data"]["id"]

        # Create endpoint owned by admin
        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET",
            "path": "/api/reassign-test",
            "status_code": 200,
            "response_body": "reassignable",
            "owner_id": 1,
            "is_active": True,
        })
        body = await resp.json()
        ep_id = body["data"]["id"]

        # Reassign to new user
        resp = await client.put(f"/admin/api/endpoints/{ep_id}", json={
            "owner_id": new_user_id,
        })
        assert resp.status == 200

        # Verify: admin token should now 404
        resp = await client.get("/api/reassign-test", headers={"stub-x-token": "admin"})
        assert resp.status == 404

        # New user token should work
        resp = await client.get("/api/reassign-test", headers={"stub-x-token": "owneruser"})
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_08_multi_tenant_isolation(self, client):
        """多租户隔离：不同 token 看到不同的端点"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Create endpoints owned by different users
        for owner_id, path in [(1, "/api/a-only"), (None, "/api/pub")]:
            await client.post("/admin/api/endpoints", json={
                "method": "GET",
                "path": path,
                "status_code": 200,
                "response_body": path,
                "owner_id": owner_id,
                "is_active": True,
            })

        # Public endpoint accessible to anyone
        r = await client.get("/api/pub")
        assert r.status == 200

        r = await client.get("/api/pub", headers={"stub-x-token": "admin"})
        assert r.status == 200

        # Owner-only endpoint: admin can see, anonymous cannot
        r = await client.get("/api/a-only")
        assert r.status == 404

        r = await client.get("/api/a-only", headers={"stub-x-token": "admin"})
        assert r.status == 200
