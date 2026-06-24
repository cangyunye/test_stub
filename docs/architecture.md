# Mock Server 架构与模块图

## 一、总体架构

```
+==========================================================================+
|                          MOCK SERVER v1.0                                |
|                    Python 3.11 + aiohttp + SQLAlchemy 2.0                |
+==========================================================================+
|                                                                          |
|  +------------------+  +------------------+  +------------------+       |
|  |   HTTP CLIENT    |  |  BROWSER (Web)   |  |   TERMINAL       |       |
|  |  curl / httpx    |  |  Chrome/Firefox  |  |   bash / zsh     |       |
|  +--------+---------+  +--------+---------+  +--------+---------+       |
|           |                     |                     |                  |
+-----------+---------------------+---------------------+------------------+
|           |                     |                     |                  |
|  +--------v---------+  +--------v---------+  +--------v---------+       |
|  |   HTTP MOCK      |  |   WEB ADMIN UI   |  |   ASCII CLI      |       |
|  |   /api/*         |  |   /admin/*       |  |   mock-server     |       |
|  |                  |  |                  |  |   cmd             |       |
|  |  - catch-all     |  |  - login.html    |  |  - start          |       |
|  |  - dynamic route |  |  - index.html    |  |  - status         |       |
|  |  - response eng. |  |  - endpoints     |  |  - add-endpoint   |       |
|  |  - delay/error   |  |  - logs          |  |  - add-ws         |       |
|  |  - request log   |  |  - users         |  |  - list-endpoints |       |
|  +--------+---------+  +--------+---------+  |  - clear-logs    |       |
|           |                     |             +--------+---------+       |
+-----------+---------------------+---------------------+------------------+
|           |                     |                     |                  |
|  +--------v---------------------v---------------------v---------+       |
|  |                    CORE ENGINE (aiohttp)                       |       |
|  |                                                                |       |
|  |  +----------------+  +----------------+  +----------------+    |       |
|  |  | Route Router   |  | ResponseEngine |  | WebSocket Mgr |    |       |
|  |  | (aiohttp)     |  | (response_eng) |  | (websocket.py)|    |       |
|  |  |                |  |                |  |                |    |       |
|  |  | - catch-all    |  | - jinja2 tmpl  |  | - echo mode    |    |       |
|  |  | - match path   |  | - condition    |  | - auto push    |    |       |
|  |  | - method filter|  | - delay inject |  | - template     |    |       |
|  |  +--------+-------+  | - error inject |  +--------+-------+    |       |
|  |           |          +--------+-------+           |             |       |
|  |           |                   |                   |             |       |
|  |  +--------v-------------------v-------------------v-------+    |       |
|  |  |              AUTH & RBAC MIDDLEWARE                     |    |       |
|  |  |                                                         |    |       |
|  |  |  +----------------+  +----------------+                 |    |       |
|  |  |  | Session Store  |  | Permission     |                 |    |       |
|  |  |  | (memory)       |  | Checker        |                 |    |       |
|  |  |  +----------------+  +----------------+                 |    |       |
|  |  +---------------------------------------------------------+    |       |
|  |                                                                |       |
|  +--------------------------------+-------------------------------+       |
|                                   |                                       |
|  +--------------------------------v-------------------------------+       |
|  |                    DATA ACCESS (SQLAlchemy 2.0)                 |       |
|  |                                                                |       |
|  |  +----------------+  +----------------+  +----------------+    |       |
|  |  | Async Engine   |  | Async Session  |  | ORM Models     |    |       |
|  |  |                |  |                |  |                |    |       |
|  |  | sqlite+aiosqlit|  | expire_on_commi|  | Endpoint       |    |       |
|  |  | postgresql+asy |  | =False         |  | RequestLog     |    |       |
|  |  |                |  |                |  | WebSocketCh.   |    |       |
|  |  |                |  |                |  | User/Role/Menu |    |       |
|  |  +----------------+  +----------------+  +----------------+    |       |
|  |                                                                |       |
|  +--------------------------------+-------------------------------+       |
|                                   |                                       |
|  +--------------------------------v-------------------------------+       |
|  |                    PERSISTENCE                                  |       |
|  |                                                                |       |
|  |  +--------------------+  +--------------------+                 |       |
|  |  |  SQLite3 (file)   |  |  PostgreSQL (opt) |                 |       |
|  |  |  mock_server.db   |  |  MOCK_DATABASE_URL|                 |       |
|  |  +--------------------+  +--------------------+                 |       |
|  |                                                                |       |
|  +----------------------------------------------------------------+       |
|                                                                          |
+==========================================================================+
```

## 二、模块依赖关系

```
+==========================================================================+
|                        MODULE DEPENDENCY GRAPH                           |
+==========================================================================+
|                                                                          |
|  +------------------+                                                    |
|  |   config.py      |  <-- pydantic-settings, env MOCK_*                |
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
|  |  - Jinja2 Template                    |                             |
|  |  - condition matching                 |                             |
|  |  - delay injection                    |                             |
|  |  - error rate injection               |                             |
|  +------------------+--------------------+                             |
|                     |                                                    |
|  +------------------v--------------------+  +------------------+       |
|  |         routes.py                      |  |  websocket.py    |       |
|  |         (HTTP 动态路由)                 |  |  (WebSocket)     |       |
|  |  - dynamic_handler()                   |  |  - ws_handler()  |       |
|  |  - register_dynamic_routes()           |  |  - auto_push()   |       |
|  |  - request logging                     |  |  - echo_mode     |       |
|  +------------------+--------------------+  +--------+---------+       |
|                     |                                |                   |
|  +------------------v--------------------------------v---------+       |
|  |                      auth.py                                |       |
|  |                      (认证中间件)                            |       |
|  |  - session_middleware                                       |       |
|  |  - require_permission()                                     |       |
|  |  - create_session() / destroy_session()                     |       |
|  +------------------+--------------------+-------+              |       |
|                     |                    |       |              |       |
|  +------------------v----+  +------------v-------+------------v-------+
|  |   auth_views.py       |  |  admin_routes.py   |  user_api.py       |
|  |   (认证 API)          |  |  admin_pages.py    |  role_api.py       |
|  |  - login_api          |  |  (静态页路由/缓存)  |  menu_api.py       |
|  |  - logout_api         |  |                    |  endpoint_api.py   |
|  |  - me_api             |  |  - /admin/*.html   |  websocket_api.py  |
|  |  - change_pw_api      |  |  - /admin/         |  log_api.py        |
|  |                       |  |                    |  dashboard_api.py  |
|  +-----------------------+  +--------------------+  +------------------+
|                                                       |
|  +----------------------------------------------------v---------+     |
|  |                      server.py                                |     |
|  |                      (应用工厂)                                |     |
|  |  - create_app()                                               |     |
|  |  - on_startup: init_db -> seed -> register_routes             |     |
|  |  - middlewares: session_middleware                            |     |
|  |  - routes: admin API + static pages + mock catch-all           |     |
|  +----------------------------------------------------+---------+     |
|                                                       |                 |
|  +----------------------------------------------------v---------+     |
|  |                      cli.py                                   |     |
|  |                      (ASCII 终端面板)                          |     |
|  |  - start  (启动服务)                                          |     |
|  |  - status (状态面板)                                          |     |
|  |  - add-endpoint                                               |     |
|  |  - add-ws                                                     |     |
|  |  - list-endpoints                                             |     |
|  |  - clear-logs                                                 |     |
|  +---------------------------------------------------------------+     |
|                                                                          |
|  +------------------+  +------------------+                             |
|  |  seed.py         |  |  tests/          |                             |
|  |  (数据初始化)     |  |  (测试套件)       |                             |
|  |  - admin/testuser|  |  - conftest.py   |                             |
|  |  - roles/menus   |  |  - test_*.py     |                             |
|  |  - test endpoints|  |                  |                             |
|  +------------------+  +------------------+                             |
|                                                                          |
+==========================================================================+
```

## 三、HTTP 请求处理流程

```
+==========================================================================+
|                    HTTP REQUEST FLOW (Mock Endpoint)                     |
+==========================================================================+
|                                                                          |
|   CLIENT                                                                 |
|     |                                                                    |
|     |  GET /api/users HTTP/1.1                                           |
|     |  (optional) stub-x-token: admin                                    |
|     v                                                                    |
+--------------------------------------------------------------------------+
|   AIOHTTP SERVER                                                         |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- Skip auth for non-/admin paths             |
|   | (auth.py)        |      All mock endpoints are public               |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  (No auth required - path doesn't start with /admin)        |
|            v                                                             |
|   +------------------+                                                   |
|   | dynamic_handler  |  <-- Catch-all route /{path:.*}                  |
|   | (routes.py)      |                                                   |
|   |                  |  1. Extract stub-x-token -> resolve owner user    |
|   |                  |  2. Query: match method+path+owner_id+is_active   |
|   |                  |  3. Fallback: match public endpoint (owner NULL)  |
|   +--------+---------+                                                   |
|            |                                                             |
|            v                                                             |
|   +------------------+                                                   |
|   | ResponseEngine   |  <-- Build response                               |
|   | (response_engine)|                                                   |
|   |                  |  4. Check delay_ms -> asyncio.sleep()             |
|   |                  |  5. Check error_rate -> random 500 injection      |
|   |                  |  6. Match condition_rules -> branch response      |
|   |                  |  7. Jinja2 render template with request data      |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  Response: status=200, body={"users": [...]}               |
|            v                                                             |
|   +------------------+                                                   |
|   | RequestLog       |  <-- INSERT INTO request_logs (...)              |
|   | (routes.py)      |                                                   |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK                                            |
|            |  Content-Type: application/json                             |
|            v                                                             |
+--------------------------------------------------------------------------+
|   CLIENT                                                                 |
+==========================================================================+
```

## 四、Admin 登录认证流程

```
+==========================================================================+
|                    AUTH FLOW (Admin Login)                               |
+==========================================================================+
|                                                                          |
|   BROWSER --> GET /admin/login                                           |
|     |                                                                    |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- /admin/login is whitelisted, skip auth     |
|   +--------+---------+                                                   |
|            |                                                             |
|            v                                                             |
|   +------------------+                                                   |
|   | make_page_handler|  <-- Load login.html from static/ directory      |
|   | (admin_pages.py) |      Return raw HTML (no Jinja2)                  |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK: <html>...login form...</html>             |
|            v                                                             |
|   BROWSER  |  User submits: POST /admin/api/auth/login                   |
|     |      |  {"username":"admin","password":"admin123"}                  |
|     v                                                                    |
|   +------------------+                                                   |
|   | login_api        |  <-- Validate credentials                        |
|   | (auth_views.py)  |                                                   |
|   |                  |  1. SELECT * FROM users WHERE username=?          |
|   |                  |  2. bcrypt.checkpw(password, hash)                |
|   |                  |  3. If superuser: permissions=["*"]               |
|   |                  |     else: query roles -> menus -> permissions     |
|   |                  |  4. Build menu tree                               |
|   |                  |  5. create_session() -> uuid4                     |
|   |                  |  6. Store in SESSION_STORE (in-memory dict)       |
|   |                  |  7. Update last_login_at                          |
|   |                  |  8. Set-Cookie: mock_session_id=xxx; HttpOnly      |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200: {"code":200,"data":{"user":...,"menus":...}}  |
|            |  Set-Cookie: mock_session_id=xxx                            |
|            v                                                             |
|   BROWSER  |  (cookie set, redirects to /admin/index.html)               |
|     |      |                                                              |
|     |  GET /admin/index.html (with Cookie)                               |
|     v                                                                    |
|   +------------------+                                                   |
|   | session_middleware|  <-- Check Cookie: mock_session_id              |
|   |                  |  <-- Lookup in SESSION_STORE                     |
|   |                  |  <-- Check TTL (1 hour)                          |
|   |                  |  <-- Inject request[USER_KEY] & request[PERM_KEY]|
|   +--------+---------+                                                   |
|            |                                                             |
|            |  (Auth PASSED)                                              |
|            v                                                             |
|   +------------------+                                                   |
|   | make_page_handler|  <-- Load index.html from static/ directory      |
|   | (admin_pages.py) |      Static HTML, no Jinja2 rendering             |
|   +--------+---------+                                                   |
|            |                                                             |
|            |  HTTP/1.1 200 OK: <html>...dashboard...</html>               |
|            v                                                             |
+==========================================================================+
```

## 五、RBAC 权限校验流程

```
+==========================================================================+
|                    PERMISSION CHECK FLOW                                 |
+==========================================================================+
|                                                                          |
|   REQUEST: DELETE /admin/api/users/3                                     |
|     |                                                                    |
|     v                                                                    |
|   1. session_middleware                                                  |
|      - Extract Cookie: mock_session_id                                   |
|      - Lookup SESSION_STORE[session_id]                                  |
|      - Inject request[USER_KEY] = {id, username, ...}                   |
|      - Inject request[PERMISSIONS_KEY] = ["*"] (superuser)               |
|                                                                          |
|     v                                                                    |
|   2. user_delete_api (user_api.py)                                       |
|      - Call require_permission(request, "users:delete")                  |
|                                                                          |
|     v                                                                    |
|   3. require_permission (auth.py)                                        |
|      +------------------+                                                |
|      | Is superuser?    | --YES--> ALLOW                                 |
|      +--------+---------+                                                |
|               | NO                                                       |
|               v                                                          |
|      +------------------+                                                |
|      | "users:delete" in| --YES--> ALLOW                                 |
|      | permissions[]?   |                                                |
|      +--------+---------+                                                |
|               | NO                                                       |
|               v                                                          |
|      +------------------+                                                |
|      | HTTP 403         |                                                |
|      | {"code":403,     |                                                |
|      | "message":"权限不足"} |                                            |
|      +------------------+                                                |
|                                                                          |
+==========================================================================+
```

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
|  |    password_hash         |    code        |         |    name        ||
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
|         |    FK   | PK id          |         | PK id          |         |
|         +-------->|    owner_id    |         |    endpoint_id |<--------+
|                    |    method      |<--------|    method      |   FK   |
|                    |    path        |   1:N   |    path        |         |
|                    |    status_code |         |    query_params|         |
|                    |    response_body         |    request_headers|      |
|                    |    response_headers      |    request_body |         |
|                    |    content_type |         |    response_status|      |
|                    |    delay_ms     |         |    response_body|       |
|                    |    error_rate   |         |    duration_ms  |       |
|                    |    condition_rules       |    client_ip    |       |
|                    |    is_active    |         |    created_at   |       |
|                    |    created_at   |         +----------------+        |
|                    |    updated_at   |                                  |
|                    +----------------+                                   |
|         |                                                                 |
|         |         +----------------+                                     |
|         |         | WebSocketChannel|                                    |
|         |         |----------------|                                     |
|         |         | PK id          |                                     |
|         |         |    path        |                                     |
|         |         |    message_template                                  |
|         |         |    auto_push_interval                                |
|         |         |    echo_mode   |                                     |
|         |         |    is_active   |                                     |
|         |         |    created_at  |                                     |
|         |         +----------------+                                     |
|         |                                                                |
+---------+----------------------------------------------------------------+
|                                                                          |
|  RELATIONSHIPS:                                                          |
|  - User -> Endpoint   : 1:N (owner_id FK)                               |
|  - User <-> Role      : M:N via UserRole                                |
|  - Role <-> Menu      : M:N via RoleMenu (with permissions JSON)         |
|  - Menu <-> Menu      : 1:N self-reference (parent_id)                  |
|  - Endpoint -> RequestLog : 1:N (endpoint_id FK)                        |
|                                                                          |
+==========================================================================+
```

## 七、测试架构

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
|  |             |  | test_integration_flow   |  | test_seed   |         |
|  +-------------+  +-------------------------+  +-------------+         |
|                                                                          |
|  TEST DB: sqlite+aiosqlite:///:memory: (in-memory, auto-create tables)  |
|                                                                          |
+==========================================================================+
```
