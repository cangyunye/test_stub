from aiohttp import web
from sqlalchemy import select, func
from mock_server.db import AsyncSessionLocal
from mock_server.models import WebSocketChannel
from mock_server.auth import require_permission


def _serialize(ch: WebSocketChannel) -> dict:
    return {
        "id": ch.id,
        "path": ch.path,
        "message_template": ch.message_template,
        "auto_push_interval": ch.auto_push_interval,
        "echo_mode": ch.echo_mode,
        "is_active": ch.is_active,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


async def websocket_channel_list_api(request: web.Request):
    """GET /admin/api/websocket-channels"""
    await require_permission(request, "endpoints:view")
    page = int(request.query.get("page", 1))
    page_size = int(request.query.get("page_size", 20))
    keyword = request.query.get("keyword", "")

    async with AsyncSessionLocal() as session:
        stmt = select(WebSocketChannel)
        if keyword:
            stmt = stmt.where(WebSocketChannel.path.ilike(f"%{keyword}%"))
        total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.order_by(WebSocketChannel.id.desc()).offset((page - 1) * page_size).limit(page_size)
        channels = (await session.execute(stmt)).scalars().all()
        items = [_serialize(ch) for ch in channels]

    return web.json_response({
        "code": 200, "message": "success",
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
    })


async def websocket_channel_get_api(request: web.Request):
    """GET /admin/api/websocket-channels/{id}"""
    await require_permission(request, "endpoints:view")
    ch_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ch = await session.get(WebSocketChannel, ch_id)
        if not ch:
            return web.json_response({"code": 404, "message": "通道不存在", "data": None}, status=404)
        return web.json_response({"code": 200, "message": "success", "data": _serialize(ch)})


async def websocket_channel_create_api(request: web.Request):
    """POST /admin/api/websocket-channels"""
    await require_permission(request, "endpoints:create")
    data = await request.json()
    async with AsyncSessionLocal() as session:
        ch = WebSocketChannel(
            path=data["path"],
            message_template=data.get("message_template", "{}"),
            auto_push_interval=int(data.get("auto_push_interval", 0) or 0),
            echo_mode=bool(data.get("echo_mode", False)),
            is_active=data.get("is_active", True),
        )
        session.add(ch)
        await session.commit()
        return web.json_response({"code": 201, "message": "通道创建成功", "data": _serialize(ch)})


async def websocket_channel_update_api(request: web.Request):
    """PUT /admin/api/websocket-channels/{id}"""
    await require_permission(request, "endpoints:edit")
    ch_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        ch = await session.get(WebSocketChannel, ch_id)
        if not ch:
            return web.json_response({"code": 404, "message": "通道不存在", "data": None}, status=404)
        if "path" in data:
            ch.path = data["path"]
        if "message_template" in data:
            ch.message_template = data["message_template"]
        if "auto_push_interval" in data:
            ch.auto_push_interval = int(data["auto_push_interval"] or 0)
        if "echo_mode" in data:
            ch.echo_mode = bool(data["echo_mode"])
        if "is_active" in data:
            ch.is_active = bool(data["is_active"])
        await session.commit()
        return web.json_response({"code": 200, "message": "通道更新成功", "data": _serialize(ch)})


async def websocket_channel_delete_api(request: web.Request):
    """DELETE /admin/api/websocket-channels/{id}"""
    await require_permission(request, "endpoints:delete")
    ch_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ch = await session.get(WebSocketChannel, ch_id)
        if ch:
            await session.delete(ch)
            await session.commit()
        return web.json_response({"code": 200, "message": "通道删除成功", "data": None})


async def websocket_channel_toggle_api(request: web.Request):
    """PATCH /admin/api/websocket-channels/{id}/toggle"""
    await require_permission(request, "endpoints:edit")
    ch_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ch = await session.get(WebSocketChannel, ch_id)
        if not ch:
            return web.json_response({"code": 404, "message": "通道不存在", "data": None}, status=404)
        ch.is_active = not ch.is_active
        await session.commit()
        return web.json_response({"code": 200, "message": "success", "data": _serialize(ch)})