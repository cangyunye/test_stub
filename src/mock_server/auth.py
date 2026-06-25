import uuid
import time
from aiohttp import web
from typing import Optional

# 内存 Session 存储（生产环境可扩展为 Redis）
SESSION_STORE: dict[str, dict] = {}
SESSION_TTL = 3600  # 1小时

# Request 存储键
USER_KEY = web.RequestKey("user", dict)
PERMISSIONS_KEY = web.RequestKey("permissions", list)

# 需要认证的根路径页面（非系统页面位于根路径，系统页面在 /admin 下）
ROOT_PROTECTED = {"/", "/index.html", "/endpoints.html", "/logs.html", "/chat.html"}


@web.middleware
async def session_middleware(request: web.Request, handler):
    # 排除登录页和登录 API 的认证检查
    if request.path in ("/admin/login", "/admin/login.html", "/admin/api/auth/login"):
        return await handler(request)

    # Mock 端点请求免认证（/api/* 和任意非系统路径）
    if not request.path.startswith("/admin") and request.path not in ROOT_PROTECTED:
        return await handler(request)

    # 静态资源免认证
    if request.path.startswith("/admin/static/"):
        return await handler(request)

    # API 请求检查 session
    is_api = request.path.startswith("/admin/api/")
    session_id = request.cookies.get("mock_session_id")
    if not session_id or session_id not in SESSION_STORE:
        if is_api:
            return web.json_response(
                {"code": 401, "message": "未登录或会话已过期", "data": None},
                status=401
            )
        raise web.HTTPFound("/admin/login")

    # 检查 Session 过期
    session = SESSION_STORE[session_id]
    if time.time() - session["created_at"] > SESSION_TTL:
        del SESSION_STORE[session_id]
        if is_api:
            return web.json_response(
                {"code": 401, "message": "会话已过期", "data": None},
                status=401
            )
        raise web.HTTPFound("/admin/login")

    # 将用户信息注入 request
    request[USER_KEY] = session["user"]
    request[PERMISSIONS_KEY] = session.get("permissions", [])

    return await handler(request)


async def require_permission(request: web.Request, permission: str):
    user_data = request.get(USER_KEY, {})
    if user_data and user_data.get("is_superuser"):
        return True
    perms = request.get(PERMISSIONS_KEY, [])
    if permission not in perms:
        raise web.HTTPForbidden(
            body='{"code": 403, "message": "权限不足", "data": null}'
        )
    return True


def create_session(user_data: dict, permissions: list) -> str:
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "user": user_data,
        "permissions": permissions,
        "created_at": time.time(),
    }
    return session_id


def destroy_session(session_id: str):
    SESSION_STORE.pop(session_id, None)
