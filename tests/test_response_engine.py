import pytest
import time
from mock_server.response_engine import ResponseEngine
from mock_server.models import Endpoint


@pytest.mark.asyncio
async def test_basic_response():
    ep = Endpoint(method="GET", path="/", status_code=200, response_body='{"ok": true}')
    status, body, headers = await ResponseEngine.build_response(ep, {})
    assert status == 200
    assert body == '{"ok": true}'


@pytest.mark.asyncio
async def test_jinja2_template():
    ep = Endpoint(method="GET", path="/user/{{id}}", status_code=200, response_body='{"id": {{user_id}}}')
    status, body, _ = await ResponseEngine.build_response(ep, {"user_id": 42})
    assert '"id": 42' in body


@pytest.mark.asyncio
async def test_delay_injection():
    ep = Endpoint(method="GET", path="/", status_code=200, response_body="{}", delay_ms=100)
    start = time.monotonic()
    await ResponseEngine.build_response(ep, {})
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed >= 90


@pytest.mark.asyncio
async def test_error_injection():
    ep = Endpoint(method="GET", path="/", status_code=200, response_body="{}", error_rate=1.0)
    status, body, _ = await ResponseEngine.build_response(ep, {})
    assert status == 500


@pytest.mark.asyncio
async def test_condition_rule_match():
    ep = Endpoint(
        method="POST", path="/login", status_code=200, response_body='{"default": true}',
        condition_rules=[
            {"condition": {"role": "admin"}, "response_body": '{"admin": true}', "status_code": 200}
        ]
    )
    status, body, _ = await ResponseEngine.build_response(ep, {"role": "admin"})
    assert body == '{"admin": true}'


@pytest.mark.asyncio
async def test_condition_rule_no_match():
    ep = Endpoint(
        method="POST", path="/login", status_code=200, response_body='{"default": true}',
        condition_rules=[
            {"condition": {"role": "admin"}, "response_body": '{"admin": true}', "status_code": 200}
        ]
    )
    status, body, _ = await ResponseEngine.build_response(ep, {"role": "user"})
    assert body == '{"default": true}'
