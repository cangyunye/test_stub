# Mock Server 架构与模块图

---

## 一、总体架构图

```
+==========================================================================+
|                          MOCK SERVER v1.0                                |
|                    Python 3.11 + aiohttp + SQLAlchemy 2.0                |
+==========================================================================+
|                                                                          |
|  +------------------+  +------------------+  +------------------+       |
|  |   HTTP CLIENT    |  |  BROWSER (Web)   |  |   TERMININAL     |       |
|  |  curl / httpx    |  |  Chrome/Firefox  |  |   bash / zsh     |       |
|  +--------+---------+  +--------+---------+  +--------+---------+       |
|           |                     |                     |                  |
+-----------+---------------------+---------------------+------------------+
|           |                     |                     |                  |
|  +--------v---------+  +--------v---------+  +--------v---------+      |
|  |   HTTP MOCK      |  |   WEB ADMIN UI   |  |   ASCII CLI      |      |
|  |   /api/*         |  |   /admin/*       |  |   mock-server    |      |
|  |                  |  |                  |  |   cmd            |      |
|  |  - dynamic route |  |  - login         |  |  - start         |      |
|  |  - response eng. |  |  - dashboard     |  |  - status        |      |
|  |  - delay/error   |  |  - endpoints     |  |  - add-endpoint  |      |
|  |  - request log   |  |  - websockets    |  |  - add-ws        |      |
|  +--------+---------+  |  - logs          |  |  - list          |      |
|           |            |  - settings      |  |  - clear-logs    |      |
|           |            +--------+---------+  +--------+---------+      |
|           |                     |                     |                  |
+-----------+---------------------+---------------------+------------------+
|           |                     |                     |                  |
|  +--------v---------------------v---------------------v---------+      |
|  |                    CORE ENGINE (aiohttp)                       |      |
|  |                                                                |      |
|  |  +----------------+  +----------------+  +----------------+   |      |
|  |  | Route Registry |  | ResponseEngine |  | WebSocket Mgr  |   |      |
|  |  |                |  |                |  |                |   |      |
|  |  | - match path   |  | - jinja2 tmpl  |  | - echo mode    |   |      |
|  |  | - method filter|  | - condition    |  | - auto push    |   |      |
|  |  | - path params  |  | - delay inject |  | - broadcast    |   |      |
|  |  +--------+-------+  | - error inject |  +--------+-------+   |      |
|  |           |          +--------+-------+           |            |      |
|  |           |                   |                   |            |      |
|  |  +--------v-------------------v-------------------v-------+   |      |
|  |  |              AUTH & RBAC MIDDLEWARE                     |   |      |
|  |  |                                                         |   |      |
|  |  |  +----------------+  +----------------+  +-----------+  |   |      |
|  |  |  | Session Store  |  | Permission     |  | Cookie    |  |   |      |
|  |  |  | (memory/Redis) |  | Checker        |  | Manager   |  |   |      |
|  |  |  +----------------+  +----------------+  +-----------+  |   |      |
|  |  +---------------------------------------------------------+   |      |
|  |                                                                |      |
|  +--------------------------------+-------------------------------+      |
|                                   |                                      |
|  +--------------------------------v-------------------------------+      |
|  |                    DATA ACCESS LAYER (SQLAlchemy 2.0)          |      |
|  |                                                                |      |
|  |  +----------------+  +----------------+  +----------------+   |      |
|  |  | Async Engine   |  | Async Session  |  | ORM Models     |   |      |
|  |  |                |  |                |  |                |   |      |
|  |  | sqlite+aiosqlit|  | expire_on_commi|  | Endpoint       |   |      |
|  |  | postgresql+asy |  | =False         |  | RequestLog     |   |      |
|  |  |                |  |                |  | WebSocketCh.   |   |      |
|  |  |                |  |                |  | User/Role/Menu |   |      |
|  |  +----------------+  +----------------+  +----------------+   |      |
|  |                                                                |      |
|  +--------------------------------+-------------------------------+      |
|                                   |                                      |
|  +--------------------------------v-------------------------------+      |
|  |                    PERSISTENCE LAYER                            |      |
|  |                                                                |      |
|  |  +--------------------+  +--------------------+                |      |
|  |  |  SQLite3 (file)   |  |  PostgreSQL (opt) |                |      |
|  |  |  mock_server.db   |  |  mock_server      |                |      |
|  |  +--------------------+  +--------------------+                |      |
|  |                                                                |      |
|  +----------------------------------------------------------------+      |
|                                                                          |
+==========================================================================+
```

---

## 二、模块依赖关系图

```
+==========================================================================+
|                        MODULE DEPENDENCY GRAPH                           |
+==========================================================================+
|                                                                          |
|  +------------------+                                                    |
|  |   config.py      |  <-- pydantic-settings, os.environ                |
|  |   (配置中心)      |                                                    |
|  +--------+---------+                                                    |
|           |                                                              |
|  +--------v---------+  +------------------+                             |
|  |   db.py          |  |   models.py      |                             |
|  |   (数据库引擎)    |  |   (ORM 模型)      |                             |
|  |                  |<->|                  |                             |
|  |  - engine        |  |  - Endpoint      |                             |
|  |  - AsyncSession  |  |  - RequestLog    |                             |
|  |  - Base          |  |  - WebSocketCh.  |                             |
|  |  - init_db()     |  |  - User/Role/Menu|                             |
|  +--------+---------+  +------------------+                             |
|           |                    ^                                         |
|           |                    |                                         |
|  +--------v--------------------v---------+                             |
|  |         response_engine.py            |                             |
|  |         (响应引擎)                     |                             |
|  |  - jinja2 Template                     |                             |
|  |  - condition matching                  |                             |
|  |  - delay injection                     |                             |
|  |  - error rate injection                |                             |
|  +------------------+--------------------+                             |
|                     |                                                    |
|  +------------------v--------------------+  +------------------+       |
|  |         routes.py                      |  |  websocket.py    |       |
|  |         (HTTP 动态路由)                 |  |  (WebSocket)     |       |
|  |  - dynamic_handler()                   |  |  - ws_handler()  |       |
|  |  - register_routes()                   |  |  - auto_push()   |       |
|  |  - request logging                     |  |  - echo_mode     |       |
|  +------------------+--------------------+  +--------+---------+       |
|                     |                                |                   |
|  +------------------v--------------------------------v---------+       |
|  |                      auth.py                                |       |
|  |                      (认证中间件)                            |       |
|  |  - session_middleware                                       |       |
|  |  - require_permission()                                     |       |
|  |  - create_session() / destroy_session()                     |       |
|  +------------------+--------------------+--------------------+       |
|                     |                    |                   |           |
|  +------------------v----+  +------------v------+  +--------v---------+|
|  |   auth_views.py       |  |  admin_views.py   |  |  user_api.py     ||
|  |   (认证视图)           |  |  (管理界面视图)    |  |  (用户管理API)   ||
|  |  - login_view         |  |  - dashboard      |  |  - list/create   ||
|  |  - login_api          |  |  - endpoints      |  |  - update/delete ||
|  |  - logout_api         |  |  - logs           |  |  - reset_pw      ||
|  |  - me_api             |  |  - websocket_ch.  |  +------------------+|
|  |  - change_pw_api      |  +-------------------+                      |
|  +-----------------------+                                               |
|                                                                          |
|  +------------------+  +------------------+  +------------------+       |
|  |  role_api.py     |  |  menu_api.py     |  |  admin_routes.py |       |
|  |  (角色管理API)    |  |  (菜单管理API)    |  |  (路由注册)       |       |
|  |  - list/create   |  |  - tree/create   |  |  - /admin/*      |       |
|  |  - update/delete |  |  - update/delete |  |  - /admin/api/*  |       |
|  |  - permissions   |  |                  |  |                  |       |
|  +------------------+  +------------------+  +--------+---------+       |
|                                                       |                  |
|  +----------------------------------------------------v---------+      |
|  |                      server.py                                |      |
|  |                      (应用工厂)                                |      |
|  |  - create_app()                                               |      |
|  |  - on_startup: init_db -> seed -> register routes             |      |
|  |  - middlewares: session_middleware                            |      |
|  |  - routes: admin + auth + user + role + menu + mock + ws      |      |
|  +----------------------------------------------------+---------+      |
|                                                       |                  |
|  +----------------------------------------------------v---------+      |
|  |                      cli.py                                   |      |
|  |                      (ASCII 终端面板)                          |      |
|  |  - start  (启动服务)                                          |      |
|  |  - status (状态面板)                                          |      |
|  |  - add-endpoint                                               |      |
|  |  - add-ws                                                     |      |
|  |  - list-endpoints                                             |      |
|  |  - clear-logs                                                 |      |
|  +---------------------------------------------------------------+      |
|                                                                          |
|  +------------------+  +------------------+  +------------------+       |
|  |  seed.py         |  |  alembic/        |  |  tests/          |       |
|  |  (数据初始化)     |  |  (数据库迁移)     |  |  (测试套件)       |       |
|  |  - default admin |  |  - env.py        |  |  - conftest.py   |       |
|  |  - default roles |  |  - versions/     |  |  - test_*.py     |       |
|  |  - default menus |  |                  |  |                  |       |
|  +------------------+  +------------------+  +------------------+       |
|                                                                          |
+==========================================================================+
```

---

## 三、数据流图（HTTP 请求处理）

```
+==========================================================================+
|                    HTTP REQUEST FLOW (Mock Endpoint)                     |
+==========================================================================+
|                                                                          |
|   CLIENT                                                                 |
|     |                                                                    |
|     |  GET /api/users HTTP/1.1                                           |
|     |  Host: localhost:8080                                              |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   AIOHTTP SERVER                                                         |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- Check Cookie: mock_session_id              |
|   | (auth.py)        |  <-- Skip for /api/* (public mock endpoints)    |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  (No auth required for mock endpoints)                      |
|            v                                                             |
|   +------------------+                                                   |
|   | dynamic_handler  |  <-- Match method + path in Endpoint table       |
|   | (routes.py)      |                                                   |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  1. Query DB: SELECT * FROM endpoints                       |
|            |     WHERE method='GET' AND path='/api/users'                |
|            |     AND is_active = TRUE                                    |
|            v                                                             |
|   +------------------+                                                   |
|   | ResponseEngine   |  <-- Build response                               |
|   | (response_engine)|                                                   |
|   |                  |  2. Check delay_ms -> asyncio.sleep()             |
|   |                  |  3. Check error_rate -> random injection          |
|   |                  |  4. Match condition_rules -> branch response      |
|   |                  |  5. Jinja2 render template with request data      |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  Response: status=200, body={"users": [...]}               |
|            v                                                             |
|   +------------------+                                                   |
|   | RequestLog       |  <-- Persist to DB                                |
|   | (routes.py)      |  INSERT INTO request_logs (...)                   |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK                                            |
|            |  Content-Type: application/json                             |
|            |  {"users": [...]}                                           |
|            v                                                             |
+--------------------------------------------------------------------------+
|   CLIENT                                                                 |
|     |                                                                    |
|     |  Receive response                                                  |
|     v                                                                    |
+==========================================================================+
```

---

## 四、数据流图（Admin 登录认证）

```
+==========================================================================+
|                    AUTH FLOW (Admin Login)                               |
+==========================================================================+
|                                                                          |
|   BROWSER                                                                |
|     |                                                                    |
|     |  GET /admin/login                                                  |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   AIOHTTP SERVER                                                         |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- /admin/login is WHITELISTED, skip auth     |
|   +--------+---------+                                                   |
|            |                                                             |
|            v                                                             |
|   +------------------+                                                   |
|   | login_view       |  <-- Return login.html (inline HTML)             |
|   | (auth_views.py)  |                                                   |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK                                            |
|            |  <html>...login form...</html>                              |
|            v                                                             |
+--------------------------------------------------------------------------+
|   BROWSER                                                                |
|     |                                                                    |
|     |  User fills form: admin / admin123                                 |
|     |                                                                    |
|     |  POST /admin/api/auth/login                                        |
|     |  Content-Type: application/json                                    |
|     |  {"username":"admin","password":"admin123"}                         |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   AIOHTTP SERVER                                                         |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- /admin/api/auth/login WHITELISTED          |
|   +--------+---------+                                                   |
|            |                                                             |
|            v                                                             |
|   +------------------+                                                   |
|   | login_api        |  <-- Validate credentials                        |
|   | (auth_views.py)  |                                                   |
|   |                  |  1. SELECT * FROM users WHERE username='admin'    |
|   |                  |  2. bcrypt.checkpw(password, password_hash)       |
|   |                  |  3. Query roles -> menus -> permissions           |
|   |                  |  4. Build menu tree                               |
|   |                  |  5. create_session() -> uuid4                     |
|   |                  |  6. Store in SESSION_STORE[session_id]            |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK                                            |
|            |  Set-Cookie: mock_session_id=xxx; HttpOnly; Path=/         |
|            |  {"code":200,"data":{"user":...,"menus":...}}               |
|            v                                                             |
+--------------------------------------------------------------------------+
|   BROWSER                                                                |
|     |                                                                    |
|     |  Store cookie, render dashboard with menus                         |
|     |                                                                    |
|     |  GET /admin/ (with Cookie)                                         |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   AIOHTTP SERVER                                                         |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- Check Cookie: mock_session_id               |
|   |                  |  <-- Validate in SESSION_STORE                    |
|   |                  |  <-- Check TTL (1 hour)                           |
|   |                  |  <-- Inject request["user"] & request["permissions"]|
|   +--------+---------+                                                   |
|            |                                                             |
|            |  (Auth PASSED)                                              |
|            v                                                             |
|   +------------------+                                                   |
|   | dashboard_view   |  <-- Render dashboard.html                        |
|   | (admin_views.py) |                                                   |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK                                            |
|            |  <html>...dashboard...</html>                               |
|            v                                                             |
+--------------------------------------------------------------------------+
|   BROWSER                                                                |
|     |                                                                    |
|     |  Display admin dashboard                                           |
|     v                                                                    |
+==========================================================================+
```

---

## 五、RBAC 权限校验流程

```
+==========================================================================+
|                    PERMISSION CHECK FLOW                                 |
+==========================================================================+
|                                                                          |
|   REQUEST: DELETE /admin/api/users/3                                     |
|     |                                                                    |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   1. session_middleware                                                  |
|      - Extract Cookie: mock_session_id                                   |
|      - Lookup SESSION_STORE[session_id]                                  |
|      - Inject request["user"] = {id, username, display_name, ...}       |
|      - Inject request["permissions"] = ["users:view", "users:create", ...]|
|                                                                          |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   2. user_delete_api (user_api.py)                                       |
|      - Call require_permission("users:delete")                           |
|                                                                          |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   3. Permission Check Logic                                              |
|      +------------------+                                                |
|      | Is superuser?    | --YES--> ALLOW                                 |
|      +--------+---------+                                                |
|               | NO                                                       |
|               v                                                          |
|      +------------------+                                                |
|      | "users:delete" in| --YES--> ALLOW                                 |
|      | permissions?     |                                                |
|      +--------+---------+                                                |
|               | NO                                                       |
|               v                                                          |
|      +------------------+                                                |
|      | Return 403       |                                                |
|      | {"code":403,     |                                                |
|      |  "message":"权限不足"} |                                           |
|      +------------------+                                                |
|                                                                          |
+==========================================================================+
```

---

## 六、ER 实体关系图

```
+==========================================================================+
|                         ENTITY RELATIONSHIP DIAGRAM                      |
+==========================================================================+
|                                                                          |
|  +----------------+         +----------------+         +----------------+|
|  |    User        |         |    Role        |         |    Menu        ||
|  |----------------|         |----------------|         |----------------||
|  | PK id          |<------->| PK id          |<------->| PK id          ||
|  |    username    |  M:N    |    name        |  M:N    |    code        ||
|  |    password_hash        |    code        |         |    name        ||
|  |    display_name|         |    is_active   |         |    path        ||
|  |    is_active   |         +----------------+         |    icon        ||
|  |    is_superuser|                ^                   |    parent_id   ||
|  |    created_at  |                |                   |    sort_order  ||
|  |    last_login  |         +-----+-----+             |    is_active   ||
|  +----------------+         |  UserRole |             +----------------+|
|         ^                   |-----------|                      ^        |
|         |                   | PK user_id|                      |        |
|         |                   | PK role_id|                      |        |
|         |                   +-----------+               +-------+-------+|
|         |                                               |   RoleMenu    ||
|         |                                               |---------------||
|         |                                               | PK role_id   ||
|         |                                               | PK menu_id   ||
|         |                                               |    permissions||
|         |                                               |    (JSON)    ||
|         |                                               +---------------+|
|         |                                                                |
|         |         +----------------+         +----------------+         |
|         |         |   Endpoint     |         |   RequestLog   |         |
|         |         |----------------|         |----------------|         |
|         |         | PK id          |         | PK id          |         |
|         |         |    method      |<--------|    endpoint_id |         |
|         |         |    path        |   1:N   |    method      |         |
|         |         |    status_code |         |    path        |         |
|         |         |    response_body         |    query_params|         |
|         |         |    delay_ms    |         |    req_headers |         |
|         |         |    error_rate  |         |    req_body    |         |
|         |         |    is_active   |         |    resp_status |         |
|         |         +----------------+         |    resp_body   |         |
|         |                                    |    duration_ms |         |
|         |         +----------------+         |    client_ip   |         |
|         |         | WebSocketChannel |       |    created_at  |         |
|         |         |----------------|         +----------------+         |
|         |         | PK id          |                                     |
|         |         |    path        |                                     |
|         |         |    echo_mode   |                                     |
|         |         |    auto_push   |                                     |
|         |         |    is_active   |                                     |
|         |         +----------------+                                     |
|         |                                                                |
+---------+----------------------------------------------------------------+
|                                                                          |
|  RELATIONSHIPS:                                                          |
|  - User <-> Role      : M:N via UserRole                                 |
|  - Role <-> Menu      : M:N via RoleMenu (with permissions JSON)         |
|  - Menu <-> Menu      : 1:N self-reference (parent_id)                   |
|  - Endpoint <-> RequestLog : 1:N                                         |
|                                                                          |
+==========================================================================+
```

---

## 七、部署架构图

```
+==========================================================================+
|                      DEPLOYMENT ARCHITECTURE                             |
+==========================================================================+
|                                                                          |
|  +------------------+     +------------------+     +------------------+ |
|  |   Developer      |     |   CI/CD          |     |   Production     | |
|  |   Workstation    |     |   Pipeline       |     |   Server         | |
|  |                  |     |                  |     |                  | |
|  |  $ mock-server   |     |  1. pytest       |     |  $ mock-server   | |
|  |    start         |     |  2. build        |     |    start         | |
|  |                  |     |  3. deploy       |     |    --host 0.0.0.0| |
|  |  Local SQLite    |     |                  |     |    --port 8080   | |
|  +--------+---------+     +--------+---------+     +--------+---------+ |
|           |                        |                        |            |
|           |  git push              |  docker build          |            |
|           +------------------------+------------------------>            |
|                                    |                                     |
|                           +--------v---------+                          |
|                           |  Docker Image    |                          |
|                           |  mock-server:1.0 |                          |
|                           |                  |                          |
|                           |  - Python 3.11   |                          |
|                           |  - aiohttp       |                          |
|                           |  - SQLAlchemy    |                          |
|                           +--------+---------+                          |
|                                    |                                     |
|                           +--------v---------+                          |
|                           |  Container       |                          |
|                           |  Port: 8080      |                          |
|                           |  Volume: data/   |                          |
|                           |    (SQLite)      |                          |
|                           +------------------+                          |
|                                                                          |
|  ENVIRONMENT VARIABLES:                                                  |
|  - MOCK_HOST=0.0.0.0                                                     |
|  - MOCK_PORT=8080                                                        |
|  - MOCK_DATABASE_URL=sqlite+aiosqlite:///data/mock_server.db             |
|  - MOCK_LOG_RETENTION_DAYS=7                                             |
|                                                                          |
+==========================================================================+
```

---

## 八、测试架构图

```
+==========================================================================+
|                         TEST ARCHITECTURE                                |
+==========================================================================+
|                                                                          |
|  +------------------+  +------------------+  +------------------+       |
|  |  pytest          |  |  pytest-aiohttp  |  |  pytest-asyncio  |       |
|  |  (测试框架)       |  |  (aiohttp client)|  |  (async fixtures)|       |
|  +--------+---------+  +--------+---------+  +--------+---------+       |
|           |                     |                     |                  |
|           +---------------------+---------------------+                  |
|                                 |                                        |
|                    +------------v------------+                           |
|                    |      conftest.py        |                           |
|                    |  - event_loop fixture   |                           |
|                    |  - db_session fixture   |                           |
|                    |  - client fixture       |                           |
|                    +------------+------------+                           |
|                                 |                                        |
|         +-----------------------+-----------------------+                |
|         |                       |                       |                |
|  +------v------+  +------------v------------+  +------v------+         |
|  | Unit Tests  |  |  Integration Tests      |  |  E2E Tests  |         |
|  |             |  |                         |  |             |         |
|  | test_models |  | test_http_mock          |  | test_admin  |         |
|  | test_resp   |  | test_websocket_mock     |  | test_auth   |         |
|  | _engine     |  | test_response_engine    |  | test_cli    |         |
|  +-------------+  +-------------------------+  +-------------+         |
|                                                                          |
|  TEST DB: sqlite+aiosqlite:///:memory:                                   |
|  COVERAGE: pytest --cov=mock_server --cov-report=html                    |
|                                                                          |
+==========================================================================+
```

---

## 九、任务执行路线图

```
+==========================================================================+
|                      TASK EXECUTION ROADMAP                              |
+==========================================================================+
|                                                                          |
|  Phase 1: FOUNDATION                                                     |
|  +--------+  +--------+  +--------+                                     |
|  | Task 1 |->| Task 2 |->| Task 3 |                                     |
|  | Init   |  | Config |  | Response|                                     |
|  | Project|  | + DB   |  | Engine |                                     |
|  +--------+  +--------+  +--------+                                     |
|       |           |           |                                          |
|       v           v           v                                          |
|  pyproject.toml  models.py  response_engine.py                          |
|  README.md       db.py      tests/test_response_engine.py               |
|                  config.py                                               |
|                                                                          |
|  Phase 2: CORE ENGINE                                                    |
|  +--------+  +--------+  +--------+                                     |
|  | Task 4 |->| Task 5 |->| Task 6 |                                     |
|  | HTTP   |  | WebSock|  | Admin  |                                     |
|  | Routes |  | et     |  | UI     |                                     |
|  +--------+  +--------+  +--------+                                     |
|       |           |           |                                          |
|       v           v           v                                          |
|  routes.py    websocket.py  admin_routes.py                             |
|  server.py                  admin_views.py                              |
|  tests/test_http_mock.py    templates/*.html                            |
|                             tests/test_admin_ui.py                      |
|                                                                          |
|  Phase 3: AUTHENTICATION                                                 |
|  +--------+  +--------+                                                 |
|  | Task 11|->| Task 12|                                                 |
|  | Auth   |  | Seed   |                                                 |
|  | + RBAC |  | Data   |                                                 |
|  +--------+  +--------+                                                 |
|       |           |                                                      |
|       v           v                                                      |
|  auth.py        seed.py                                                  |
|  auth_views.py                                                             |
|  user_api.py                                                             |
|  role_api.py                                                             |
|  menu_api.py                                                             |
|  tests/test_auth.py                                                      |
|                                                                          |
|  Phase 4: TOOLS & MIGRATION                                              |
|  +--------+  +--------+  +--------+                                     |
|  | Task 7 |->| Task 8 |->| Task 9 |                                     |
|  | CLI    |  | Alembic|  | Tests  |                                     |
|  | Panel  |  | Migrate|  | Suite  |                                     |
|  +--------+  +--------+  +--------+                                     |
|       |           |           |                                          |
|       v           v           v                                          |
|  cli.py        alembic/     conftest.py                                 |
|  tests/test_cli.py          tests/test_*.py                             |
|                                                                          |
|  Phase 5: DOCUMENTATION                                                  |
|  +--------+                                                             |
|  | Task 10|                                                             |
|  | Docs   |                                                             |
|  +--------+                                                             |
|       |                                                                  |
|       v                                                                  |
|  docs/api_examples.md                                                    |
|                                                                          |
+==========================================================================+
```

---

## 十、技术栈层次图

```
+==========================================================================+
|                        TECH STACK LAYERS                                 |
+==========================================================================+
|                                                                          |
|  +--------------------+  +--------------------+  +--------------------+  |
|  |   Presentation     |  |   Presentation     |  |   Presentation     |  |
|  |   Layer (Web)      |  |   Layer (CLI)      |  |   Layer (API)      |  |
|  |                    |  |                    |  |                    |  |
|  |  Jinja2 Templates  |  |  Click Commands    |  |  JSON REST API     |  |
|  |  - login.html      |  |  - status          |  |  - /admin/api/*    |  |
|  |  - dashboard.html  |  |  - add-endpoint    |  |  - /api/* (mock)   |  |
|  |  - endpoints.html  |  |  - list            |  |                    |  |
|  +--------+-----------+  +--------+-----------+  +--------+-----------+  |
|           |                       |                       |              |
|  +--------v-----------+  +--------v-----------+  +--------v-----------+  |
|  |   Controller       |  |   Controller       |  |   Controller       |  |
|  |   Layer            |  |   Layer            |  |   Layer            |  |
|  |                    |  |                    |  |                    |  |
|  |  admin_views.py    |  |  cli.py            |  |  auth_views.py     |  |
|  |  auth_views.py     |  |                    |  |  user_api.py       |  |
|  |  user_api.py       |  |                    |  |  role_api.py       |  |
|  |  role_api.py       |  |                    |  |  menu_api.py       |  |
|  |  menu_api.py       |  |                    |  |  routes.py         |  |
|  +--------+-----------+  +--------------------+  +--------+-----------+  |
|           |                                               |              |
|  +--------v-----------------------------------------------v-----------+  |
|  |                        Service Layer                                 |  |
|  |                                                                      |  |
|  |  +----------------+  +----------------+  +----------------+         |  |
|  |  | ResponseEngine |  | Auth Service   |  | Route Registry |         |  |
|  |  |                |  |                |  |                |         |  |
|  |  | - jinja2       |  | - session      |  | - match        |         |  |
|  |  | - condition    |  | - permission   |  | - register     |         |  |
|  |  | - delay/error  |  | - bcrypt       |  | - dynamic      |         |  |
|  |  +----------------+  +----------------+  +----------------+         |  |
|  |                                                                      |  |
|  +--------+-------------------------------+---------------------------+  |
|           |                               |                              |
|  +--------v-----------+  +----------------v-----------+                  |
|  |   Data Access      |  |   Data Access              |                  |
|  |   Layer (ORM)      |  |   Layer (ORM)              |                  |
|  |                    |  |                            |                  |
|  |  SQLAlchemy 2.0    |  |  SQLAlchemy 2.0            |                  |
|  |  - AsyncSession    |  |  - AsyncSession            |                  |
|  |  - Declarative     |  |  - Declarative             |                  |
|  |  - Relationships   |  |  - Relationships           |                  |
|  +--------+-----------+  +----------------+-----------+                  |
|           |                               |                              |
|  +--------v-----------+  +----------------v-----------+                  |
|  |   Database         |  |   Database                 |                  |
|  |   SQLite3          |  |   PostgreSQL (optional)    |                  |
|  |   (aiosqlite)      |  |   (asyncpg)                |                  |
|  +--------------------+  +----------------------------+                  |
|                                                                          |
+==========================================================================+
```

---

*文档生成时间: 2026-06-23*
*对应计划文档: /workspace/plan-mock-server.md*
