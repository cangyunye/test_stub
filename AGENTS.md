# Mock Server — HTTP/WebSocket Stub Server with Web UI

Python 3.11 + aiohttp 测试桩服务。支持多租户端点隔离、Jinja2 模板响应、延迟/错误率注入、Web 管理界面（RBAC）、ASCII CLI 控制面板、SQLite/PostgreSQL 双后端。

## Commands

| 用途 | 命令 |
|------|------|
| 快速启动 | `./run.sh [port]` |
| 安装（dev） | `pip install -e ".[dev]"` |
| 启动服务 | `mock-server start --port 8080` |
| 控制面板 | `mock-server status` |
| 运行测试 | `pytest` |
| 单文件测试 | `pytest -xvs tests/test_integration_flow.py` |
| Make | `make install` / `make run` / `make test` |

- 测试配置：`[tool.pytest.ini_options]` asyncio_mode=auto, testpaths=["tests"]
- 入口点：`mock_server.cli:main`，也支持 `python -m mock_server`
- 默认账号：`admin / admin123`

## Architecture

源码位于 `src/mock_server/`，20+ 模块：

| 模块 | 职责 |
|------|------|
| `config.py` | pydantic-settings，环境前缀 `MOCK_` |
| `db.py` | SQLAlchemy 2.0 async engine + sessionmaker |
| `models.py` | ORM：Endpoint, RequestLog, WebSocketChannel, User, Role, Menu |
| `server.py` | aiohttp app factory |
| `routes.py` | 动态 Mock 端点路由，兜底 handler |
| `response_engine.py` | 延迟 → 错误率 → 条件规则 → Jinja2 渲染 |
| `websocket.py` | WebSocket 处理（echo/auto-push/template） |
| `cli.py` | Click CLI：start / status / add-endpoint / add-ws |
| `auth.py` | Session 中间件 |
| `auth_views.py` | 登录/登出/改密码 API |
| `admin_routes.py` | 管理 UI 静态页面路由 |
| `admin_pages.py` | 静态 HTML 页面加载与缓存 |
| `user_api.py` | 用户 CRUD API |
| `role_api.py` | 角色 CRUD + 权限绑定 API |
| `menu_api.py` | 菜单树 CRUD API |
| `endpoint_api.py` | HTTP 端点 CRUD + toggle API |
| `websocket_api.py` | WebSocket 通道 CRUD + toggle API |
| `log_api.py` | 请求日志 API |
| `dashboard_api.py` | 仪表盘统计 API |
| `seed.py` | 首次启动自动填充默认数据（用户/角色/菜单/测试端点） |
| `static/` | 前端原型 HTML 页面 |

测试位于 `tests/`，使用 `pytest-asyncio` + 内存 SQLite。

## Conventions

- **Async/await**: 全部异步，`async with AsyncSessionLocal() as session`
- **SQLAlchemy 2.0 Mapped**: `Mapped[...]` 类型注解
- **Import**: `mock_server.*` 绝对 import
- **API 响应格式**: `{"code": int, "message": str, "data": ...}`
- **多租户**: 请求头 `stub-x-token`，无 token 命中公共端点（`owner_id IS NULL`）
- **测试**: `@pytest.mark.asyncio` + `async def`；`conftest.py` 提供 `db_session` fixture
- **配置**: pydantic-settings，环境变量覆盖（`MOCK_DATABASE_URL` 等）
- **前端**: 纯静态 HTML 位于 `src/mock_server/static/`，由 `admin_pages.py` 缓存后以 `text/html` 返回；JS 调 `/admin/api/*`

## Seed Data

首次启动自动创建：

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| `admin` | `admin123` | 超级管理员 | 全权限 |
| `testuser` | `test123` | 测试人员 | 用于测试多租户 |

预置 Mock 端点：

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/hello` | GET | 公共端点，返回欢迎消息 |
| `/api/echo` | POST | 公共端点，原样返回请求体 |
| `/api/delay` | GET | 公共端点，1 秒延迟 |
| `/api/admin-only` | GET | admin 专属端点，需 `stub-x-token: admin` |
| `/api/admin-action` | POST | admin 专属端点 |
| `/ws/echo` | WS | 公共 WebSocket 回声通道 |

## Notes

<!-- 快速记录 — 后续按需补充 -->
