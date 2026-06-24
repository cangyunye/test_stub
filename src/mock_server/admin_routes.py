from aiohttp import web
from mock_server.config import settings
from mock_server.admin_pages import make_page_handler, index_redirect


def setup_admin_routes(app: web.Application):
    """注册管理后台静态页面路由（前端原型）"""
    prefix = settings.admin_path

    # 根路径重定向到仪表盘
    app.router.add_get(f"{prefix}/", index_redirect)

    # 静态页面（login 免认证，其余需认证）
    app.router.add_get(f"{prefix}/login", make_page_handler("login"))
    app.router.add_get(f"{prefix}/login.html", make_page_handler("login"))
    app.router.add_get(f"{prefix}/index.html", make_page_handler("index"))
    app.router.add_get(f"{prefix}/endpoints.html", make_page_handler("endpoints"))
    app.router.add_get(f"{prefix}/logs.html", make_page_handler("logs"))
    app.router.add_get(f"{prefix}/users.html", make_page_handler("users"))