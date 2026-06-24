import os
import aiohttp_jinja2
import jinja2
from aiohttp import web
from mock_server.db import init_db
from mock_server.routes import register_dynamic_routes, dynamic_handler
from mock_server.websocket import register_websocket_routes
from mock_server.admin_routes import setup_admin_routes
from mock_server.auth import session_middleware
from mock_server.auth_views import login_api, logout_api, me_api, change_password_api
from mock_server.user_api import user_list_api, user_create_api, user_update_api, user_delete_api, user_reset_password_api
from mock_server.role_api import role_list_api, role_create_api, role_update_api, role_delete_api, role_permissions_api, role_permissions_update_api
from mock_server.menu_api import menu_tree_api, menu_create_api, menu_update_api, menu_delete_api
from mock_server.endpoint_api import (
    endpoint_list_api, endpoint_get_api, endpoint_create_api,
    endpoint_update_api, endpoint_delete_api, endpoint_toggle_api,
)
from mock_server.websocket_api import (
    websocket_channel_list_api, websocket_channel_get_api, websocket_channel_create_api,
    websocket_channel_update_api, websocket_channel_delete_api, websocket_channel_toggle_api,
)
from mock_server.log_api import log_list_api, log_get_api, log_clear_api
from mock_server.dashboard_api import dashboard_stats_api
from mock_server.seed import seed_data
from mock_server.config import settings


async def on_startup(app: web.Application):
    await init_db()
    await seed_data()
    await register_dynamic_routes(app)
    await register_websocket_routes(app)


async def on_cleanup(app: web.Application):
    pass


def create_app() -> web.Application:
    app = web.Application(middlewares=[session_middleware])

    # Jinja2 仍用于响应体模板渲染（ResponseEngine），此处保留 loader
    aiohttp_jinja2.setup(app, loader=jinja2.DictLoader({}))

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    prefix = settings.admin_path

    # Auth routes
    app.router.add_post(f"{prefix}/api/auth/login", login_api)
    app.router.add_post(f"{prefix}/api/auth/logout", logout_api)
    app.router.add_get(f"{prefix}/api/auth/me", me_api)
    app.router.add_post(f"{prefix}/api/auth/change-password", change_password_api)

    # Dashboard
    app.router.add_get(f"{prefix}/api/dashboard/stats", dashboard_stats_api)

    # Endpoint management routes
    app.router.add_get(f"{prefix}/api/endpoints", endpoint_list_api)
    app.router.add_post(f"{prefix}/api/endpoints", endpoint_create_api)
    app.router.add_get(f"{prefix}/api/endpoints/{{id}}", endpoint_get_api)
    app.router.add_put(f"{prefix}/api/endpoints/{{id}}", endpoint_update_api)
    app.router.add_delete(f"{prefix}/api/endpoints/{{id}}", endpoint_delete_api)
    app.router.add_route("PATCH", f"{prefix}/api/endpoints/{{id}}/toggle", endpoint_toggle_api)

    # WebSocket channel management routes
    app.router.add_get(f"{prefix}/api/websocket-channels", websocket_channel_list_api)
    app.router.add_post(f"{prefix}/api/websocket-channels", websocket_channel_create_api)
    app.router.add_get(f"{prefix}/api/websocket-channels/{{id}}", websocket_channel_get_api)
    app.router.add_put(f"{prefix}/api/websocket-channels/{{id}}", websocket_channel_update_api)
    app.router.add_delete(f"{prefix}/api/websocket-channels/{{id}}", websocket_channel_delete_api)
    app.router.add_route("PATCH", f"{prefix}/api/websocket-channels/{{id}}/toggle", websocket_channel_toggle_api)

    # Request log routes
    app.router.add_get(f"{prefix}/api/logs", log_list_api)
    app.router.add_delete(f"{prefix}/api/logs", log_clear_api)
    app.router.add_get(f"{prefix}/api/logs/{{id}}", log_get_api)

    # User management routes
    app.router.add_get(f"{prefix}/api/users", user_list_api)
    app.router.add_post(f"{prefix}/api/users", user_create_api)
    app.router.add_put(f"{prefix}/api/users/{{id}}", user_update_api)
    app.router.add_delete(f"{prefix}/api/users/{{id}}", user_delete_api)
    app.router.add_post(f"{prefix}/api/users/{{id}}/reset-password", user_reset_password_api)

    # Role management routes
    app.router.add_get(f"{prefix}/api/roles", role_list_api)
    app.router.add_post(f"{prefix}/api/roles", role_create_api)
    app.router.add_put(f"{prefix}/api/roles/{{id}}", role_update_api)
    app.router.add_delete(f"{prefix}/api/roles/{{id}}", role_delete_api)
    app.router.add_get(f"{prefix}/api/roles/{{id}}/permissions", role_permissions_api)
    app.router.add_put(f"{prefix}/api/roles/{{id}}/permissions", role_permissions_update_api)

    # Menu management routes
    app.router.add_get(f"{prefix}/api/menus/tree", menu_tree_api)
    app.router.add_post(f"{prefix}/api/menus", menu_create_api)
    app.router.add_put(f"{prefix}/api/menus/{{id}}", menu_update_api)
    app.router.add_delete(f"{prefix}/api/menus/{{id}}", menu_delete_api)

    # Admin UI 静态页面路由
    setup_admin_routes(app)

    # 兜底路由：未匹配到的请求也走动态处理器
    app.router.add_route("*", "/{path:.*}", dynamic_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)