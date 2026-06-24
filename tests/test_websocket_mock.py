import pytest
from mock_server.server import create_app


@pytest.mark.asyncio
async def test_websocket_unconfigured_path(aiohttp_client):
    app = create_app()
    client = await aiohttp_client(app)
    # 未配置的 WebSocket 路径应该返回 404（HTTP 层面）
    # 因为 register_websocket_routes 没有注册 /ws/unknown
    # 兜底路由 dynamic_handler 会返回 404
    with pytest.raises(Exception):
        await client.ws_connect("/ws/unknown")
