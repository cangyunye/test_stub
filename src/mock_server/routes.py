import time
import logging
from aiohttp import web
from sqlalchemy import select
from mock_server.db import AsyncSessionLocal
from mock_server.models import Endpoint, RequestLog, User
from mock_server.response_engine import ResponseEngine

logger = logging.getLogger("mock_server.routes")


async def dynamic_handler(request: web.Request) -> web.Response:
    start = time.monotonic()
    method = request.method
    path = request.path

    # 从请求头提取 stub-x-token 识别调用者
    stub_token = request.headers.get("stub-x-token", "")
    owner_id = None
    if stub_token:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.username == stub_token, User.is_active == True)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                owner_id = user.id

    async with AsyncSessionLocal() as session:
        # 查找匹配的 endpoint：先匹配 owner_id，再匹配公共端点
        stmt = select(Endpoint).where(
            Endpoint.method == method,
            Endpoint.path == path,
            Endpoint.is_active == True,
            Endpoint.owner_id == owner_id
        )
        result = await session.execute(stmt)
        endpoint = result.scalar_one_or_none()

        # 如果未找到用户专属端点，尝试公共端点
        if endpoint is None and owner_id is not None:
            stmt = select(Endpoint).where(
                Endpoint.method == method,
                Endpoint.path == path,
                Endpoint.is_active == True,
                Endpoint.owner_id == None
            )
            result = await session.execute(stmt)
            endpoint = result.scalar_one_or_none()

        request_data = {
            "method": method,
            "path": path,
            "query": dict(request.query),
            "headers": dict(request.headers),
            "body": await request.text(),
        }

        if endpoint:
            status, body, headers = await ResponseEngine.build_response(endpoint, request_data)
        else:
            status, body, headers = 404, '{"error": "not found"}', {"Content-Type": "application/json"}

        duration_ms = int((time.monotonic() - start) * 1000)

        # 记录日志
        log = RequestLog(
            endpoint_id=endpoint.id if endpoint else None,
            method=method,
            path=path,
            query_params=request_data["query"],
            request_headers=request_data["headers"],
            request_body=request_data["body"],
            response_status=status,
            response_body=body,
            duration_ms=duration_ms,
            client_ip=request.remote or "",
        )
        session.add(log)
        await session.commit()

        return web.Response(status=status, body=body, headers=headers)


async def register_dynamic_routes(app: web.Application):
    """启动时从数据库加载所有公共端点并注册静态路由（仅用于日志和调试）"""
    async with AsyncSessionLocal() as session:
        stmt = select(Endpoint).where(Endpoint.is_active == True, Endpoint.owner_id == None)
        result = await session.execute(stmt)
        endpoints = result.scalars().all()
        for ep in endpoints:
            app.router.add_route(ep.method, ep.path, dynamic_handler)
            logger.info(f"[ROUTE REGISTERED] {ep.method} {ep.path} (public)")
        logger.info(f"[ROUTE SUMMARY] Total public endpoints registered: {len(endpoints)}")
