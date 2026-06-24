import asyncio
import json
from aiohttp import web
from jinja2 import Template
from sqlalchemy import select
from mock_server.db import AsyncSessionLocal
from mock_server.models import WebSocketChannel


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    path = request.path

    async with AsyncSessionLocal() as session:
        stmt = select(WebSocketChannel).where(
            WebSocketChannel.path == path,
            WebSocketChannel.is_active == True
        )
        result = await session.execute(stmt)
        channel = result.scalar_one_or_none()

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    if not channel:
        await ws.close(code=1008, message=b"Channel not configured")
        # 需要返回非101状态码让客户端知道连接被拒绝
        # 但 aiohttp WebSocketResponse 已经发送了握手响应
        # 所以直接返回 ws 对象，客户端会收到 close 帧
        return ws

    # 自动推送任务
    push_task = None
    if channel.auto_push_interval > 0:
        async def auto_push():
            while not ws.closed:
                await asyncio.sleep(channel.auto_push_interval)
                if not ws.closed:
                    template = Template(channel.message_template)
                    msg = template.render(timestamp=asyncio.get_event_loop().time())
                    await ws.send_str(msg)
        push_task = asyncio.create_task(auto_push())

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            if channel.echo_mode:
                await ws.send_str(msg.data)
            else:
                template = Template(channel.message_template)
                response = template.render(request=msg.data)
                await ws.send_str(response)
        elif msg.type == web.WSMsgType.ERROR:
            break

    if push_task:
        push_task.cancel()
    return ws


async def register_websocket_routes(app: web.Application):
    async with AsyncSessionLocal() as session:
        stmt = select(WebSocketChannel).where(WebSocketChannel.is_active == True)
        result = await session.execute(stmt)
        channels = result.scalars().all()
        for ch in channels:
            app.router.add_get(ch.path, websocket_handler)
