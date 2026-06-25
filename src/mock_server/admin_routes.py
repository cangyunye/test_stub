from aiohttp import web
from mock_server.config import settings
from mock_server.admin_pages import make_page_handler, index_redirect


def setup_admin_routes(app: web.Application):
    """注册管理后台静态页面路由（前端原型）"""
    prefix = settings.admin_path

    # 根路径 → 仪表盘
    app.router.add_get("/", index_redirect)
    app.router.add_get("/index.html", make_page_handler("index"))

    # 非系统页面位于根路径（需认证，由 middleware 保护）
    app.router.add_get("/endpoints.html", make_page_handler("endpoints"))
    app.router.add_get("/logs.html", make_page_handler("logs"))

    # 系统页面位于 /admin 下
    app.router.add_get(f"{prefix}/", index_redirect)
    app.router.add_get(f"{prefix}/login", make_page_handler("login"))
    app.router.add_get(f"{prefix}/login.html", make_page_handler("login"))
    app.router.add_get(f"{prefix}/index.html", make_page_handler("index"))
    app.router.add_get(f"{prefix}/endpoints.html", make_page_handler("endpoints"))
    app.router.add_get(f"{prefix}/logs.html", make_page_handler("logs"))
    app.router.add_get(f"{prefix}/users.html", make_page_handler("users"))