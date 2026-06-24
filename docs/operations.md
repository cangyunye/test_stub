# Mock Server 操作手册

## 目录

- [快速启动](#快速启动)
- [CLI 命令参考](#cli-命令参考)
- [Web 管理界面](#web-管理界面)
- [Mock 端点操作](#mock-端点操作)
- [WebSocket 操作](#websocket-操作)
- [多租户与 stub-x-token](#多租户与-stub-x-token)
- [用户权限管理](#用户权限管理)
- [Jinja2 响应模板](#jinja2-响应模板)
- [请求日志](#请求日志)
- [配置与环境变量](#配置与环境变量)
- [常见问题](#常见问题)

---

## 快速启动

```bash
# 一键启动（自动创建 venv + 安装依赖 + 运行）
./run.sh                     # 默认 8080
./run.sh 9090                # 指定端口

# 或使用 Make
make install                 # 安装依赖
make run PORT=8080           # 启动服务
```

首次启动自动创建默认数据：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 超级管理员（所有权限） |

---

## CLI 命令参考

### `mock-server start`

启动 Mock Server 进程。

```bash
mock-server start --host 0.0.0.0 --port 8080
```

### `mock-server status`

ASCII 控制面板，显示端点/WS/请求计数和最近 5 条请求。

```
+==========================================================================+
|                          MOCK SERVER CONTROL PANEL v1.0                    |
+==========================================================================+
|  Endpoints: 12    WS Channels: 3     Total Requests: 1247                 |
+--------------------------------------------------------------------------+
|  LAST 5 REQUESTS                                                          |
+--------+----------+----------------------+----------+--------------------+
|  TIME  | METHOD   | PATH                 | STATUS   | DURATION           |
+--------+----------+----------------------+----------+--------------------+
| 14:32  | GET      | /api/users           | 200      | 12ms               |
| 14:31  | POST     | /api/auth/login      | 401      | 45ms               |
...
```

### `mock-server add-endpoint`

创建 HTTP Mock 端点。

```bash
# 公共端点（任何请求均可命中）
mock-server add-endpoint --method GET --path /users --status 200 \
  --body '{"users":[]}' --public

# 带延迟和错误率
mock-server add-endpoint --method POST --path /login --status 200 \
  --delay 500 --error-rate 0.1 --body '{"token":"xxx"}' --public

# 用户专属端点（需携带 stub-x-token 请求头）
mock-server add-endpoint --method GET --path /my/profile --status 200 \
  --owner tester --body '{"name":"Tester"}'
```

### `mock-server add-ws`

创建 WebSocket 通道。

```bash
# 回声模式
mock-server add-ws --path /ws/echo --echo

# 自动推送模式（每 5 秒推送一条模板消息）
mock-server add-ws --path /ws/push --template '{"time":"{{ timestamp }}"}' \
  --interval 5

# 消息模板模式（用户发消息后按模板回复）
mock-server add-ws --path /ws/chat --template '{"reply":"you said: {{ request }}"}'
```

### `mock-server list-endpoints`

列出所有 HTTP 端点。

### `mock-server clear-logs`

清空所有请求日志（需确认）。

---

## Web 管理界面

服务启动后访问 `http://localhost:8080/admin/`，默认账号 `admin / admin123`。

### 页面一览

| 页面 | URL | 功能 |
|------|-----|------|
| 仪表盘 | `/admin/index.html` | 关键指标、24h 趋势图、状态码分布、最近请求 |
| 端点管理 | `/admin/endpoints.html` | HTTP 端点 + WebSocket 通道的 CRUD、启用/停用 |
| 请求日志 | `/admin/logs.html` | 日志搜索、状态码过滤、时间范围筛选、请求/响应详情 |
| 用户与权限 | `/admin/users.html` | 用户/角色/菜单权限管理 |
| 登录 | `/admin/login` | 登录页 |

### 仪表盘

- **统计卡片**：HTTP 端点数、WebSocket 通道数、今日请求量、平均响应时间
- **24h 趋势图**：柱状图显示过去 24 小时每小时的请求量
- **状态码分布**：2xx/4xx/5xx 占比及条形图，成功率
- **最近请求**：最近 8 条请求记录，可点击进入日志详情

### 端点管理

支持 HTTP 端点和 WebSocket 通道两个标签页：

**HTTP 端点**：
- 搜索按路径过滤
- 按 HTTP 方法（ALL/GET/POST/PUT/DELETE）快速筛选
- 启用/停用开关
- 编辑、删除操作
- 新建模态框：方法、路径、响应状态码、响应体（支持 Jinja2 模板）、延迟、错误率、归属用户

**WebSocket 通道**：
- 搜索按路径过滤
- 启用/停用开关
- 删除操作

### 请求日志

- 搜索路径/IP
- 状态码过滤（ALL/2xx/4xx/5xx）
- 时间范围（1h/6h/24h/7d）
- 点击一行查看详情（请求头、请求体、响应体）

### 用户与权限

**用户管理**：创建/编辑/删除用户、重置密码、分配角色

**角色管理**：创建/编辑/删除角色

**菜单权限**：针对每个角色逐菜单配置 view/create/edit/delete 权限

---

## Mock 端点操作

### 创建端点

```bash
# CLI
mock-server add-endpoint --method POST --path /api/order \
  --status 201 --body '{"order_id": 12345}' --public
```

或通过 Web UI「端点管理 → 新建端点」。

### 测试端点

```bash
# 公共端点
curl http://localhost:8080/api/order -X POST \
  -H "Content-Type: application/json" \
  -d '{"item":"test"}'

# 响应:
# HTTP/1.1 201
# {"order_id": 12345}
```

### 延迟注入

设置 `delay_ms` 后，Mock Server 会在返回响应前等待指定毫秒数：

```bash
mock-server add-endpoint --method GET --path /slow-api \
  --delay 2000 --body '{"slow":true}' --public

curl http://localhost:8080/slow-api   # 2 秒后收到响应
```

### 错误率注入

设置 `error_rate`（0.0 ~ 1.0），每次请求以该概率返回 500：

```bash
mock-server add-endpoint --method GET --path /flaky \
  --error-rate 0.3 --body '{"ok":true}' --public
# 约 30% 的请求返回 500
```

### 条件规则

响应体支持 Jinja2 模板，可根据请求参数动态渲染：

```
响应体模板：
{
  "method": "{{method}}",
  "path": "{{path}}",
  "query": {{query|tojson}},
  "body": {{body|tojson}}
}
```

---

## WebSocket 操作

### 三种模式

| 模式 | 说明 |
|------|------|
| 回声模式（echo） | 客户端发送的任何消息原样返回 |
| 自动推送（auto-push） | 按固定间隔自动推送模板消息，模板可用 `{{ timestamp }}` |
| 消息模板（message-template） | 客户端发送消息后，用模板渲染后返回，模板可用 `{{ request }}` |

### 测试 WebSocket

```bash
# 安装 websocat
brew install websocat   # macOS

# 回声
websocat ws://localhost:8080/ws/echo
> hello
< hello

# 自动推送
websocat ws://localhost:8080/ws/push
< {"time": "1719234000"}
< {"time": "1719234005"}
< ...
```

> **注意**：WebSocket 通道仅在服务启动时注册。运行时新建的通道需要重启服务才能生效。

---

## 多租户与 stub-x-token

Mock Server 支持多租户隔离：

1. **公共端点**（`owner_id IS NULL`）：任何请求均可命中
2. **用户专属端点**（`owner_id = 用户 ID`）：仅携带对应 `stub-x-token` 的请求可命中

```bash
# 创建用户专属端点
mock-server add-endpoint --method GET --path /my/secret \
  --owner tester --body '{"secret":"data"}' --public

# 无 token → 不匹配（可能返回 404 或命中公共端点）
curl http://localhost:8080/my/secret
# 404

# 携带 token → 命中
curl http://localhost:8080/my/secret -H "stub-x-token: tester"
# 200 {"secret": "data"}
```

`stub-x-token` 的值必须是系统中已存在的用户名。

---

## 用户权限管理

### RBAC 模型

```
用户 → 角色 → 菜单（含权限）
```

| 预置角色 | 编码 | 权限 |
|----------|------|------|
| 超级管理员 | superadmin | 所有菜单 × 所有操作（view/create/edit/delete） |
| 测试人员 | tester | Dashboard（查看）、Endpoints（查看/创建/编辑）、WebSockets（查看/创建/编辑）、Logs（查看） |
| 只读用户 | readonly | Dashboard（查看）、Endpoints（查看）、WebSockets（查看）、Logs（查看） |

### 通过 Web UI 管理

进入「用户与权限」页面：

1. **用户管理标签页**：创建/编辑用户、分配角色、启用/停用
2. **角色管理标签页**：创建/编辑角色
3. **菜单权限标签页**：对每个角色逐菜单勾选操作权限

### API 方式

```bash
# 重置密码（不指定新密码时自动生成）
curl -X POST http://localhost:8080/admin/api/users/2/reset-password \
  -H "Cookie: mock_session_id=xxx"
# 返回: {"code":200,"data":{"new_password":"aB3xK9mQpZ","generated":true}}

# 如指定密码
curl -X POST http://localhost:8080/admin/api/users/2/reset-password \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"password":"newPass123"}'
```

---

## Jinja2 响应模板

响应体支持 Jinja2 模板语法，可访问请求数据：

| 模板变量 | 说明 |
|----------|------|
| `{{ method }}` | HTTP 方法（GET/POST/...） |
| `{{ path }}` | 请求路径 |
| `{{ query }}` | 查询参数（dict） |
| `{{ headers }}` | 请求头（dict） |
| `{{ body }}` | 请求体（字符串） |

示例：根据请求参数返回不同内容

```
{% set q = query %}
{% if q.get("type") == "vip" %}
{"level": "vip", "discount": 0.8}
{% else %}
{"level": "normal", "discount": 1.0}
{% endif %}
```

---

## 请求日志

每次 HTTP 请求经过 Mock Server 时自动记录：

- 请求方法、路径、查询参数
- 请求头、请求体
- 响应状态码、响应体
- 处理耗时
- 客户端 IP
- 时间戳

可通过 Web UI「请求日志」页面或 API 查询：

```bash
# 日志列表（支持分页、过滤、时间范围）
curl "http://localhost:8080/admin/api/logs?page=1&page_size=20&status_code=4xx&time_range=24h" \
  -H "Cookie: mock_session_id=xxx"

# 日志详情
curl http://localhost:8080/admin/api/logs/42 \
  -H "Cookie: mock_session_id=xxx"

# 清空日志
curl -X DELETE http://localhost:8080/admin/api/logs \
  -H "Cookie: mock_session_id=xxx"
```

---

## 配置与环境变量

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MOCK_HOST` | `0.0.0.0` | 监听地址 |
| `MOCK_PORT` | `8080` | 监听端口 |
| `MOCK_DATABASE_URL` | `sqlite+aiosqlite:///./mock_server.db` | 数据库连接（支持 PostgreSQL） |
| `MOCK_ADMIN_PATH` | `/admin` | 管理后台路径前缀 |
| `MOCK_LOG_RETENTION_DAYS` | `7` | 日志保留天数 |

使用 PostgreSQL：

```bash
MOCK_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/mock_server" \
  mock-server start
```

---

## 常见问题

**Q：WebSocket 新建后无法连接？**

通道仅在服务启动时注册路由。新建通道后需重启 Mock Server。

**Q：端点创建后访问仍返回 404？**

1. 确认端点为启用状态
2. 确认路径和方法完全匹配（含大小写）
3. 如为专属端点，确认请求携带了正确的 `stub-x-token`
4. 检查是否存在路径更具体的兜底路由

**Q：响应体中的模板变量未渲染？**

确认端点响应体使用了 `{{ 变量名 }}` 语法，且变量名匹配请求数据字段（method/path/query/headers/body）。

**Q：登录报错但确认账号密码正确？**

确认服务已运行 `mock-server start`（CLI 命令仅供离线管理，不能替代服务进程）。

**Q：Web UI 页面空白或 API 返回 401？**

登录会话过期，刷新页面重定向到登录页。使用 Web UI 时确保 Cookie 未被浏览器拦截。

**Q：如何修改默认密码？**

登录后在 `/admin/api/auth/change-password` API 提交旧密码和新密码，或通过 Web UI 当前暂未提供修改入口（仅 API）。

```bash
curl -X POST http://localhost:8080/admin/api/auth/change-password \
  -H "Cookie: mock_session_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"admin123","new_password":"newPass456","confirm_password":"newPass456"}'
```
