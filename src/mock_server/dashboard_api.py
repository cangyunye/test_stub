from datetime import datetime, timedelta, timezone
from collections import defaultdict
from sqlalchemy import select, func, desc
from aiohttp import web
from mock_server.db import AsyncSessionLocal
from mock_server.models import Endpoint, WebSocketChannel, RequestLog
from mock_server.auth import require_permission


async def dashboard_stats_api(request: web.Request):
    """GET /admin/api/dashboard/stats"""
    await require_permission(request, "dashboard:view")
    async with AsyncSessionLocal() as session:
        endpoint_count = await session.scalar(select(func.count()).select_from(Endpoint))
        websocket_count = await session.scalar(select(func.count()).select_from(WebSocketChannel))

        # 今日请求
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        req_stmt = select(RequestLog).where(RequestLog.created_at >= since)
        total = await session.scalar(select(func.count()).select_from(req_stmt.subquery()))

        # 平均响应时间
        avg_ms = await session.scalar(
            select(func.avg(RequestLog.duration_ms)).where(RequestLog.created_at >= since)
        ) or 0

        # 状态码分布
        dist_rows = (await session.execute(
            select(RequestLog.response_status).where(RequestLog.created_at >= since)
        )).scalars().all()
        dist = {"2xx": 0, "4xx": 0, "5xx": 0, "s2xx": 0, "s4xx": 0, "s5xx": 0}
        for s in dist_rows:
            s = s or 0
            if 200 <= s < 300:
                dist["2xx"] += 1; dist["s2xx"] += 1
            elif 400 <= s < 500:
                dist["4xx"] += 1; dist["s4xx"] += 1
            elif s >= 500:
                dist["5xx"] += 1; dist["s5xx"] += 1
        success_total = dist["2xx"] + dist["4xx"] + dist["5xx"]
        success_rate = round(dist["2xx"] / success_total * 100, 1) if success_total else 0.0

        # 24h 趋势
        hourly = defaultdict(int)
        now = datetime.now(timezone.utc)
        for i in range(24):
            h = now - timedelta(hours=(23 - i))
            hourly[h.strftime("%Y-%m-%dT%H:00:00")] = 0
        rows = (await session.execute(
            select(RequestLog.created_at).where(RequestLog.created_at >= since)
        )).scalars().all()
        for c in rows:
            if c:
                key = c.strftime("%Y-%m-%dT%H:00:00")
                if key in hourly:
                    hourly[key] += 1
        hourly_trend = [{"hour": k[-8:-3], "count": v} for k, v in hourly.items()]

        # 最近请求
        recent = (await session.execute(
            select(RequestLog).order_by(desc(RequestLog.created_at)).limit(8)
        )).scalars().all()
        recent_requests = [{
            "id": r.id, "method": r.method, "path": r.path,
            "response_status": r.response_status, "duration_ms": r.duration_ms,
            "client_ip": r.client_ip,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in recent]

    return web.json_response({
        "code": 200, "message": "success",
        "data": {
            "endpoint_count": endpoint_count,
            "websocket_count": websocket_count,
            "request_count": total,
            "avg_response_ms": round(float(avg_ms), 1),
            "success_rate": success_rate,
            "status_distribution": dist,
            "hourly_trend": hourly_trend,
            "recent_requests": recent_requests,
        },
    })