import pytest
from aiohttp import web
from mock_server.server import create_app


@pytest.mark.asyncio
async def test_websocket_unconfigured_path(aiohttp_client):
    app = create_app()
    client = await aiohttp_client(app)
    # 未配置的 WebSocket 路径：dynamic_handler 捕获后委托 websocket_handler
    # 应返回 close 帧（code=1008）而非弹异常
    resp = await client.ws_connect("/ws/unknown")
    # 等待对方关闭
    msg = await resp.receive()
    assert msg.type == web.WSMsgType.CLOSE
    assert resp.close_code == 1008
