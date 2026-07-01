"""端到端集成测试：用户创建 → 端点创建 → 公共/归属端点调用 + 路由认证 + 登出流程"""
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


async def _login_as(client, username: str, password: str) -> str:
    """Login as any user, return session cookie value."""
    resp = await client.post("/admin/api/auth/login", json={
        "username": username, "password": password,
    })
    assert resp.status == 200, f"login as {username} failed"
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


class TestRouteAuth:

    @pytest.mark.asyncio
    async def test_09_root_pages_redirect_unauthenticated(self, client):
        """未登录用户访问根路径页面应重定向到 /admin/login"""
        for path in ("/", "/index.html", "/endpoints.html", "/logs.html"):
            resp = await client.get(path, allow_redirects=False)
            assert resp.status in (302, 303), f"{path} should redirect, got {resp.status}"
            location = resp.headers.get("Location", "")
            assert location == "/admin/login", f"{path} redirects to {location}, expected /admin/login"

    @pytest.mark.asyncio
    async def test_10_root_pages_accessible_after_login(self, client):
        """登录后根路径页面应正常返回 200"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.get("/", allow_redirects=False)
        assert resp.status in (302, 303), f"got {resp.status}"
        assert resp.headers.get("Location") in ("/index.html", "/admin/")

        resp = await client.get("/index.html")
        assert resp.status == 200

        resp = await client.get("/endpoints.html")
        assert resp.status == 200

        resp = await client.get("/logs.html")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_11_admin_pages_redirect_unauthenticated(self, client):
        """未登录用户访问 /admin 页面应重定向到 /admin/login"""
        for path in ("/admin/", "/admin/index.html", "/admin/endpoints.html",
                     "/admin/logs.html", "/admin/users.html"):
            resp = await client.get(path, allow_redirects=False)
            assert resp.status in (302, 303), f"{path} should redirect, got {resp.status}"
            location = resp.headers.get("Location", "")
            assert location == "/admin/login", f"{path} redirects to {location}"

    @pytest.mark.asyncio
    async def test_12_admin_pages_accessible_after_login(self, client):
        """登录后 /admin 页面应正常返回 200"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        for path in ("/admin/", "/admin/index.html", "/admin/endpoints.html",
                     "/admin/logs.html", "/admin/users.html"):
            resp = await client.get(path, allow_redirects=False)
            if resp.status in (302, 303):
                resp = await client.get(resp.headers.get("Location", ""))
            assert resp.status == 200, f"{path} returned {resp.status}"

    @pytest.mark.asyncio
    async def test_13_login_page_whitelisted(self, client):
        """登录页面无需认证即可访问"""
        resp = await client.get("/admin/login")
        assert resp.status == 200

        resp = await client.get("/admin/login.html")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_14_logout_clears_session(self, client):
        """登出后清除 session，再次访问受保护页面需重新登录"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Verify authenticated first
        resp = await client.get("/index.html")
        assert resp.status == 200

        # Logout
        resp = await client.post("/admin/api/auth/logout")
        assert resp.status == 200
        body = await resp.json()
        assert body["code"] == 200

        # Session cookie cleared — access should redirect
        resp = await client.get("/index.html", allow_redirects=False)
        assert resp.status in (302, 303)
        assert resp.headers.get("Location") == "/admin/login"

    @pytest.mark.asyncio
    async def test_15_mock_endpoints_unauthenticated(self, client):
        """Mock 端点 /api/* 无需认证即可访问"""
        resp = await client.get("/api/hello")
        assert resp.status == 200
        data = await resp.json()
        assert "message" in data


class TestPermissionAccess:

    @pytest.mark.asyncio
    async def test_16_ws_channel_create_and_connect(self, client):
        """创建 WebSocket 通道后可通过 WS 连接（动态路由）"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Create WS channel via API
        resp = await client.post("/admin/api/websocket-channels", json={
            "path": "/ws/integration-test",
            "echo_mode": True,
            "auto_push_interval": 0,
            "is_active": True,
        })
        body = await resp.json()
        assert body["code"] == 201, body

        # Connect via WebSocket (tests dynamic routing in catch-all handler)
        ws = await client.ws_connect("/ws/integration-test")
        await ws.send_str("ping")
        msg = await ws.receive()
        assert msg.type == web.WSMsgType.TEXT
        assert msg.data == "ping"
        await ws.close()

    @pytest.mark.asyncio
    async def test_17_visitor_cannot_create_endpoint(self, client):
        """只读用户（visitor）无法创建端点"""
        sid = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid)

        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET", "path": "/api/visitor-test",
            "status_code": 200, "response_body": "{}",
            "is_active": True,
        })
        assert resp.status == 403, f"expected 403, got {resp.status}"

    @pytest.mark.asyncio
    async def test_18_visitor_cannot_edit_endpoint(self, client):
        """只读用户无法编辑端点"""
        # Admin creates endpoint first
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET", "path": "/api/visitor-edit-test",
            "status_code": 200, "response_body": "original",
            "is_active": True,
        })
        ep_id = (await resp.json())["data"]["id"]

        # Visitor tries to edit
        sid2 = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid2)
        resp = await client.put(f"/admin/api/endpoints/{ep_id}", json={
            "response_body": "hacked",
        })
        assert resp.status == 403, f"expected 403, got {resp.status}"

        # Verify original content preserved
        sid3 = await _login(client)
        await _set_cookie(client, sid3)
        resp = await client.get(f"/admin/api/endpoints/{ep_id}")
        body = await resp.json()
        assert body["data"]["response_body"] == "original"

    @pytest.mark.asyncio
    async def test_19_visitor_cannot_delete_endpoint(self, client):
        """只读用户无法删除端点"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET", "path": "/api/visitor-delete-test",
            "status_code": 200, "response_body": "{}",
            "is_active": True,
        })
        ep_id = (await resp.json())["data"]["id"]

        sid2 = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid2)
        resp = await client.delete(f"/admin/api/endpoints/{ep_id}")
        assert resp.status == 403, f"expected 403, got {resp.status}"

    @pytest.mark.asyncio
    async def test_20_visitor_cannot_create_ws_channel(self, client):
        """只读用户无法创建 WebSocket 通道"""
        sid = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid)
        resp = await client.post("/admin/api/websocket-channels", json={
            "path": "/ws/visitor-test",
            "echo_mode": True,
            "is_active": True,
        })
        assert resp.status == 403, f"expected 403, got {resp.status}"

    @pytest.mark.asyncio
    async def test_21_visitor_can_view_endpoints(self, client):
        """只读用户可以查看端点列表"""
        sid = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/endpoints?page=1&page_size=10")
        assert resp.status == 200
        body = await resp.json()
        assert body["code"] == 200

    @pytest.mark.asyncio
    async def test_22_get_user_by_id(self, client):
        """GET /admin/api/users/{id} 返回用户详情"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # admin is user id=1
        resp = await client.get("/admin/api/users/1")
        assert resp.status == 200
        body = await resp.json()
        assert body["code"] == 200
        assert body["data"]["username"] == "admin"
        assert body["data"]["is_superuser"] == True
        assert "roles" in body["data"]

    @pytest.mark.asyncio
    async def test_23_get_user_not_found(self, client):
        """GET /admin/api/users/{id} 不存在时返回 404"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/users/9999")
        assert resp.status == 404
        body = await resp.json()
        assert body["code"] == 404

    @pytest.mark.asyncio
    async def test_24_visitor_cannot_view_user(self, client):
        """只读用户无 users:view 权限，获取用户详情返回 403"""
        sid = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/users/1")
        assert resp.status == 403, f"expected 403, got {resp.status}"

    @pytest.mark.asyncio
    async def test_25_admin_update_password(self, client):
        """管理员修改用户密码后新密码生效"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # Create a test user
        resp = await client.post("/admin/api/users", json={
            "username": "pwtest", "password": "old123",
            "display_name": "PW Test", "is_active": True,
        })
        body = await resp.json()
        uid = body["data"]["id"]

        # Update password
        resp = await client.put(f"/admin/api/users/{uid}", json={
            "password": "new456",
        })
        assert resp.status == 200

        # Verify login with new password works
        resp = await client.post("/admin/api/auth/login", json={
            "username": "pwtest", "password": "new456",
        })
        assert resp.status == 200, "new password should work"

        # Old password should fail
        resp = await client.post("/admin/api/auth/login", json={
            "username": "pwtest", "password": "old123",
        })
        assert resp.status == 401, "old password should fail"

    @pytest.mark.asyncio
    async def test_26_cannot_delete_last_superuser(self, client):
        """无法删除最后一个超级管理员"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.delete("/admin/api/users/1")
        assert resp.status == 400, f"expected 400, got {resp.status}"
        body = await resp.json()
        assert "无法删除" in body.get("message", "")

    @pytest.mark.asyncio
    async def test_27_cannot_deactivate_last_superuser(self, client):
        """无法停用最后一个超级管理员"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.put("/admin/api/users/1", json={
            "is_active": False,
        })
        assert resp.status == 400, f"expected 400, got {resp.status}"
        body = await resp.json()
        assert "无法停用" in body.get("message", "")


class TestSearch:

    @pytest.mark.asyncio
    async def test_28_search_endpoint_by_path(self, client):
        """搜索端点路径返回匹配结果"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/search?q=hello")
        assert resp.status == 200, f"expected 200, got {resp.status}"
        body = await resp.json()
        assert body["code"] == 200
        assert len(body["data"]["items"]) >= 1
        items = body["data"]["items"]
        ep = [i for i in items if i["type"] == "endpoint" and "/api/hello" in i["title"]]
        assert len(ep) >= 1
        assert "url" in ep[0]

    @pytest.mark.asyncio
    async def test_29_search_empty_result(self, client):
        """搜索不存在的关键词返回空列表"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/search?q=xyznonexistent12345")
        assert resp.status == 200
        body = await resp.json()
        assert body["data"]["items"] == []

    @pytest.mark.asyncio
    async def test_30_search_without_q_returns_empty(self, client):
        """不传 q 参数返回空列表"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/search")
        assert resp.status == 200
        body = await resp.json()
        assert body["data"]["items"] == []

    @pytest.mark.asyncio
    async def test_31_search_unauthenticated(self, client):
        """未登录用户搜索返回 401"""
        resp = await client.get("/admin/api/search?q=hello")
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_32_search_permission_filter_visitor(self, client):
        """visitor 用户只看到有权限的模块（无 users）"""
        sid = await _login_as(client, "visitor", "visitor123")
        await _set_cookie(client, sid)
        # 搜索所有内容
        resp = await client.get("/admin/api/search?q=admin")
        assert resp.status == 200
        body = await resp.json()
        items = body["data"]["items"]
        # visitor 没有 users:view，搜索结果不应包含 type=user
        user_items = [i for i in items if i["type"] == "user"]
        assert len(user_items) == 0, f"visitor should not see users, got {user_items}"

    @pytest.mark.asyncio
    async def test_33_search_special_chars(self, client):
        """特殊字符搜索不报错"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        for q in ("{}", "[]", "*", "(", ")", "\\"):
            resp = await client.get(f"/admin/api/search?q={q}")
            assert resp.status == 200, f"q={q} failed: {resp.status}"

    @pytest.mark.asyncio
    async def test_34_search_very_long_keyword(self, client):
        """超长关键词搜索不报错"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        q = "x" * 500
        resp = await client.get(f"/admin/api/search?q={q}")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_35_search_result_has_url_with_params(self, client):
        """搜索结果中包含带 q 和 highlight 参数的 url"""
        sid = await _login(client)
        await _set_cookie(client, sid)
        resp = await client.get("/admin/api/search?q=hello")
        assert resp.status == 200
        body = await resp.json()
        for item in body["data"]["items"]:
            assert "url" in item, f"missing url in {item}"
            assert "q=" in item["url"], f"url missing q= param: {item['url']}"
            assert "highlight=" in item["url"], f"url missing highlight= param: {item['url']}"


class TestPathQuery:

    @pytest.mark.asyncio
    async def test_36_endpoint_with_literal_question(self, client):
        """端点路径含字面 ?，支持 ? 和 %3F 两种方式访问"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        # 创建带 ? 的路径
        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET", "path": "/api/qa?foo=bar",
            "status_code": 200, "response_body": '{"ok":true}',
            "is_active": True,
        })
        body = await resp.json()
        assert body["code"] in (200, 201), body

        # 用 %3F 访问（字面 ?）
        resp = await client.get("/api/qa%3Ffoo=bar")
        assert resp.status == 200, f"%3F access expected 200, got {resp.status}"

        # 用 ? 访问（作为 query string），匹配 path + "?" + query_string
        resp = await client.get("/api/qa?foo=bar")
        assert resp.status == 200, f"? access expected 200, got {resp.status}"

    @pytest.mark.asyncio
    async def test_37_endpoint_with_question_no_query(self, client):
        """路径含 ? 但请求无 query string 时也能匹配"""
        sid = await _login(client)
        await _set_cookie(client, sid)

        resp = await client.post("/admin/api/endpoints", json={
            "method": "GET", "path": "/api/qonly?",
            "status_code": 200, "response_body": '{"ok":true}',
            "is_active": True,
        })
        body = await resp.json()
        assert body["code"] in (200, 201), body

        # %3F 访问（字面 ?）
        resp = await client.get("/api/qonly%3F")
        assert resp.status == 200, f"got {resp.status}"
