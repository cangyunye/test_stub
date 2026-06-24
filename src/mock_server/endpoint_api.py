from aiohttp import web
from sqlalchemy import select, func
from mock_server.db import AsyncSessionLocal
from mock_server.models import Endpoint, User
from mock_server.auth import require_permission


def _serialize(ep: Endpoint, owner: User | None = None) -> dict:
    return {
        "id": ep.id,
        "owner_id": ep.owner_id,
        "owner_name": owner.username if owner else None,
        "method": ep.method,
        "path": ep.path,
        "status_code": ep.status_code,
        "response_body": ep.response_body,
        "response_headers": ep.response_headers or {},
        "content_type": ep.content_type,
        "delay_ms": ep.delay_ms,
        "error_rate": ep.error_rate,
        "condition_rules": ep.condition_rules or [],
        "is_active": ep.is_active,
        "created_at": ep.created_at.isoformat() if ep.created_at else None,
        "updated_at": ep.updated_at.isoformat() if ep.updated_at else None,
    }


async def _load_endpoint(session, ep_id: int):
    ep = await session.get(Endpoint, ep_id)
    if not ep:
        return None, None
    owner = await session.get(User, ep.owner_id) if ep.owner_id else None
    return ep, owner


async def endpoint_list_api(request: web.Request):
    """GET /admin/api/endpoints"""
    await require_permission(request, "endpoints:view")
    page = int(request.query.get("page", 1))
    page_size = int(request.query.get("page_size", 20))
    method = request.query.get("method", "")
    keyword = request.query.get("keyword", "")

    async with AsyncSessionLocal() as session:
        stmt = select(Endpoint)
        if method:
            stmt = stmt.where(Endpoint.method == method.upper())
        if keyword:
            stmt = stmt.where(Endpoint.path.ilike(f"%{keyword}%"))
        total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.order_by(Endpoint.id.desc()).offset((page - 1) * page_size).limit(page_size)
        endpoints = (await session.execute(stmt)).scalars().all()

        items = []
        for ep in endpoints:
            owner = await session.get(User, ep.owner_id) if ep.owner_id else None
            items.append(_serialize(ep, owner))

    return web.json_response({
        "code": 200, "message": "success",
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
    })


async def endpoint_get_api(request: web.Request):
    """GET /admin/api/endpoints/{id}"""
    await require_permission(request, "endpoints:view")
    ep_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ep, owner = await _load_endpoint(session, ep_id)
        if not ep:
            return web.json_response({"code": 404, "message": "端点不存在", "data": None}, status=404)
        return web.json_response({"code": 200, "message": "success", "data": _serialize(ep, owner)})


async def endpoint_create_api(request: web.Request):
    """POST /admin/api/endpoints"""
    await require_permission(request, "endpoints:create")
    data = await request.json()
    async with AsyncSessionLocal() as session:
        ep = Endpoint(
            method=data.get("method", "GET").upper(),
            path=data.get("path", "/"),
            status_code=int(data.get("status_code", 200)),
            response_body=data.get("response_body", "{}"),
            response_headers=data.get("response_headers", {}),
            content_type=data.get("content_type", "application/json"),
            delay_ms=int(data.get("delay_ms", 0)),
            error_rate=float(data.get("error_rate", 0.0)),
            condition_rules=data.get("condition_rules", []),
            owner_id=data.get("owner_id"),
            is_active=data.get("is_active", True),
        )
        session.add(ep)
        await session.commit()
        owner = await session.get(User, ep.owner_id) if ep.owner_id else None
        return web.json_response({"code": 201, "message": "端点创建成功", "data": _serialize(ep, owner)})


async def endpoint_update_api(request: web.Request):
    """PUT /admin/api/endpoints/{id}"""
    await require_permission(request, "endpoints:edit")
    ep_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        ep, owner = await _load_endpoint(session, ep_id)
        if not ep:
            return web.json_response({"code": 404, "message": "端点不存在", "data": None}, status=404)
        if "method" in data:
            ep.method = data["method"].upper()
        if "path" in data:
            ep.path = data["path"]
        if "status_code" in data:
            ep.status_code = int(data["status_code"])
        if "response_body" in data:
            ep.response_body = data["response_body"]
        if "response_headers" in data:
            ep.response_headers = data["response_headers"]
        if "content_type" in data:
            ep.content_type = data["content_type"]
        if "delay_ms" in data:
            ep.delay_ms = int(data["delay_ms"])
        if "error_rate" in data:
            ep.error_rate = float(data["error_rate"])
        if "condition_rules" in data:
            ep.condition_rules = data["condition_rules"]
        if "owner_id" in data:
            ep.owner_id = data["owner_id"]
        if "is_active" in data:
            ep.is_active = data["is_active"]
        await session.commit()
        owner = await session.get(User, ep.owner_id) if ep.owner_id else None
        return web.json_response({"code": 200, "message": "端点更新成功", "data": _serialize(ep, owner)})


async def endpoint_delete_api(request: web.Request):
    """DELETE /admin/api/endpoints/{id}"""
    await require_permission(request, "endpoints:delete")
    ep_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ep = await session.get(Endpoint, ep_id)
        if ep:
            await session.delete(ep)
            await session.commit()
        return web.json_response({"code": 200, "message": "端点删除成功", "data": None})


async def endpoint_toggle_api(request: web.Request):
    """PATCH /admin/api/endpoints/{id}/toggle"""
    await require_permission(request, "endpoints:edit")
    ep_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        ep, owner = await _load_endpoint(session, ep_id)
        if not ep:
            return web.json_response({"code": 404, "message": "端点不存在", "data": None}, status=404)
        ep.is_active = not ep.is_active
        await session.commit()
        owner = await session.get(User, ep.owner_id) if ep.owner_id else None
        return web.json_response({"code": 200, "message": "success", "data": _serialize(ep, owner)})