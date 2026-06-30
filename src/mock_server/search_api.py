from aiohttp import web
from sqlalchemy import select, or_
from mock_server.db import AsyncSessionLocal
from mock_server.models import Endpoint, WebSocketChannel, RequestLog, User
from mock_server.auth import require_permission, PERMISSIONS_KEY, USER_KEY


async def search_api(request: web.Request):
    """GET /admin/api/search?q=keyword"""
    q = request.query.get("q", "").strip()
    user_data = request.get(USER_KEY, {})
    is_super = user_data and user_data.get("is_superuser", False)
    perms = request.get(PERMISSIONS_KEY, [])

    def has_perm(p: str) -> bool:
        return is_super or p in perms

    items = []
    like = f"%{q}%"

    async with AsyncSessionLocal() as session:
        if q and has_perm("endpoints:view"):
            stmt = select(Endpoint).where(
                or_(Endpoint.path.ilike(like), Endpoint.response_body.ilike(like))
            ).limit(20)
            for ep in (await session.execute(stmt)).scalars().all():
                owner_name = None
                if ep.owner_id:
                    u = await session.get(User, ep.owner_id)
                    if u:
                        owner_name = u.username
                items.append({
                    "type": "endpoint",
                    "id": ep.id,
                    "title": f"{ep.method} {ep.path}",
                    "description": (ep.response_body or "")[:80] + " · " + (owner_name or "公共"),
                    "url": f'/endpoints.html?q={q}&highlight={ep.id}',
                })

        if q and has_perm("endpoints:view"):
            stmt = select(WebSocketChannel).where(
                or_(WebSocketChannel.path.ilike(like), WebSocketChannel.message_template.ilike(like))
            ).limit(10)
            for ch in (await session.execute(stmt)).scalars().all():
                items.append({
                    "type": "websocket",
                    "id": ch.id,
                    "title": f"WS {ch.path}",
                    "description": "回声" if ch.echo_mode else "模板模式",
                    "url": f'/endpoints.html?q={q}&highlight=ws-{ch.id}',
                })

        if q and has_perm("logs:view"):
            stmt = select(RequestLog).where(
                or_(RequestLog.path.ilike(like), RequestLog.client_ip.ilike(like),
                    RequestLog.request_body.ilike(like), RequestLog.response_body.ilike(like))
            ).limit(20)
            for log in (await session.execute(stmt)).scalars().all():
                items.append({
                    "type": "log",
                    "id": log.id,
                    "title": f"{log.method} {log.path}",
                    "description": f"{log.response_status} · {log.client_ip or '—'}",
                    "url": f'/logs.html?q={q}&highlight={log.id}',
                })

        if q and has_perm("users:view"):
            stmt = select(User).where(
                or_(User.username.ilike(like), User.display_name.ilike(like))
            ).limit(10)
            for user in (await session.execute(stmt)).scalars().all():
                items.append({
                    "type": "user",
                    "id": user.id,
                    "title": user.username,
                    "description": user.display_name or "—",
                    "url": f'/admin/users.html?q={q}&highlight={user.id}',
                })

    return web.json_response({"code": 200, "message": "success", "data": {"items": items}})
