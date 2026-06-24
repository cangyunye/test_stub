import random
import asyncio
from jinja2 import Template
from mock_server.models import Endpoint


class ResponseEngine:
    @staticmethod
    async def build_response(endpoint: Endpoint, request_data: dict) -> tuple[int, str, dict]:
        # 延迟注入
        delay = endpoint.delay_ms or 0
        if delay > 0:
            await asyncio.sleep(delay / 1000)

        # 错误率注入
        error_rate = endpoint.error_rate or 0.0
        if error_rate > 0 and random.random() < error_rate:
            return 500, '{"error": "injected server error"}', {"Content-Type": "application/json"}

        # 条件规则匹配
        body = endpoint.response_body or ""
        status = endpoint.status_code or 200
        headers = dict(endpoint.response_headers or {})
        headers.setdefault("Content-Type", endpoint.content_type or "application/json")

        for rule in endpoint.condition_rules or []:
            if ResponseEngine._match_condition(rule, request_data):
                body = rule.get("response_body", body)
                status = rule.get("status_code", status)
                break

        # Jinja2 模板渲染
        template = Template(body)
        rendered_body = template.render(**request_data)

        return status, rendered_body, headers

    @staticmethod
    def _match_condition(rule: dict, request_data: dict) -> bool:
        condition = rule.get("condition", {})
        for key, expected in condition.items():
            actual = request_data.get(key)
            if actual != expected:
                return False
        return True
