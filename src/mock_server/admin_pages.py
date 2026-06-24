import os
from aiohttp import web

# 静态页面目录
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# 页面名称 → 文件名映射
_PAGES = {
    "index": "index.html",
    "endpoints": "endpoints.html",
    "logs": "logs.html",
    "users": "users.html",
    "login": "login.html",
}

# 缓存文件内容，避免每次请求都读盘
_CACHE: dict[str, str] = {}


def _load(name: str) -> str:
    if name not in _CACHE:
        path = os.path.join(_STATIC_DIR, _PAGES[name])
        with open(path, "r", encoding="utf-8") as f:
            _CACHE[name] = f.read()
    return _CACHE[name]


def make_page_handler(name: str):
    async def handler(request: web.Request) -> web.Response:
        return web.Response(text=_load(name), content_type="text/html", charset="utf-8")
    return handler


async def index_redirect(request: web.Request):
    """根路径重定向到仪表盘"""
    raise web.HTTPFound("/admin/index.html")