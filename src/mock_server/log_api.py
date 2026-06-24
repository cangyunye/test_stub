from datetime import datetime, timedelta, timezone
from aiohttp import web
from sqlalchemy import select, func, delete
from mock_server.db import AsyncSessionLocal
from mock_server.models import RequestLog
from mock_server.auth import require_permission

# time_range -> timedelta
_RANGE_MAP = {"1h": timedelta(hours=1), "6h": timedelta(hours=6),
             "24h": timedelta(hours=24), "7d": timedelta(days=7)}


def _serialize(log: RequestLog) -> dict:
    return {
        "id": log.id,
        "endpoint_id": log.endpoint_id,
        "method": log.method,
        "path": log.path,
        "query_params": log.query_params or {},
        "request_headers": log.request_headers or {},
        "request_body": log.request_body or "",
        "response_status": log.response_status,
        "status_code": log.response_status,
        "response_body": log.response_body or "",
        "duration_ms": log.duration_ms,
        "duration": log.duration_ms,
        "client_ip": log.client_ip,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


async def log_list_api(request: web.Request):
    """GET /admin/api/logs"""
    await require_permission(request, "logs:view")
    page = int(request.query.get("page", 1))
    page_size = int(request.query.get("page_size", 50))
    status_code = request.query.get("status_code", "")
    method = request.query.get("method", "")
    keyword = request.query.get("keyword", "")
    time_range = request.query.get("time_range", "")

    async with AsyncSessionLocal() as session:
        stmt = select(RequestLog)
        if status_code == "2xx":
            stmt = stmt.where(RequestLog.response_status >= 200, RequestLog.response_status < 300)
        elif status_code == "4xx":
            stmt = stmt.where(RequestLog.response_status >= 400, RequestLog.response_status < 500)
        elif status_code == "5xx":
            stmt = stmt.where(RequestLog.response_status >= 500)
        if method:
            stmt = stmt.where(RequestLog.method == method.upper())
        if keyword:
            stmt = stmt.where(
                RequestLog.path.ilike(f"%{keyword}%") | RequestLog.client_ip.ilike(f"%{keyword}%")
            )
        if time_range in _RANGE_MAP:
            since = datetime.now(timezone.utc) - _RANGE_MAP[time_range]
            stmt = stmt.where(RequestLog.created_at >= since)

        total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.order_by(RequestLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        logs = (await session.execute(stmt)).scalars().all()
        items = [_serialize(l) for l in logs]

    return web.json_response({
        "code": 200, "message": "success",
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
    })


async def log_get_api(request: web.Request):
    """GET /admin/api/logs/{id}"""
    await require_permission(request, "logs:view")
    log_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        log = await session.get(RequestLog, log_id)
        if not log:
            return web.json_response({"code": 404, "message": "日志不存在", "data": None}, status=404)
        return web.json_response({"code": 200, "message": "success", "data": _serialize(log)})


async def log_clear_api(request: web.Request):
    """DELETE /admin/api/logs"""
    await require_permission(request, "logs:delete")
    async with AsyncSessionLocal() as session:
        await session.execute(delete(RequestLog))
        await session.commit()
    return web.json_response({"code": 200, "message": "日志已清空", "data": None})