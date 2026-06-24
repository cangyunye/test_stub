import pytest
from sqlalchemy import select
from mock_server.server import create_app
from mock_server.db import AsyncSessionLocal
from mock_server.models import User, Role, Menu


@pytest.mark.asyncio
async def test_seed_data_loaded(aiohttp_client):
    app = create_app()
    client = await aiohttp_client(app)

    # 触发 on_startup 初始化
    async with AsyncSessionLocal() as session:
        admin = await session.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        assert admin.is_superuser is True

        roles = (await session.execute(select(Role))).scalars().all()
        assert len(roles) == 3

        menus = (await session.execute(select(Menu))).scalars().all()
        assert len(menus) == 13
