import pytest
from mock_server.models import Endpoint, RequestLog, WebSocketChannel, User, Role, Menu


@pytest.mark.asyncio
async def test_endpoint_creation(db_session):
    endpoint = Endpoint(method="GET", path="/test", status_code=200, response_body="{}")
    db_session.add(endpoint)
    await db_session.commit()
    assert endpoint.id is not None
    assert endpoint.method == "GET"
    assert endpoint.owner_id is None


@pytest.mark.asyncio
async def test_user_creation(db_session):
    user = User(username="tester", password_hash="hashed", display_name="Tester")
    db_session.add(user)
    await db_session.commit()
    assert user.id is not None
    assert user.username == "tester"


@pytest.mark.asyncio
async def test_endpoint_with_owner(db_session):
    user = User(username="dev1", password_hash="hashed")
    db_session.add(user)
    await db_session.flush()

    endpoint = Endpoint(method="POST", path="/api", status_code=201, response_body="{}", owner_id=user.id)
    db_session.add(endpoint)
    await db_session.commit()

    assert endpoint.owner_id == user.id
    assert endpoint.owner.username == "dev1"
