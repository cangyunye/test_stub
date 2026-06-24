# Mock Server API 使用示例

## 启动服务

```bash
mock-server start --port 8080
```

## CLI 添加端点

```bash
# 添加公共端点 GET /users
mock-server add-endpoint --method GET --path /users --status 200 --body '{"users":[]}' --public

# 添加用户专属端点 POST /login（需先登录获取 stub-x-token）
mock-server add-endpoint --method POST --path /login --status 200 --delay 500 --owner tester

# 添加 WebSocket 回声通道
mock-server add-ws --path /ws/echo --echo
```

## curl 测试用例

### 公共端点（无需 stub-x-token）

```bash
# 测试 GET /users
curl -i http://localhost:8080/users

# 预期响应:
# HTTP/1.1 200 OK
# Content-Type: application/json
# {"users":[]}
```

### 用户专属端点（需携带 stub-x-token）

```bash
# 测试 POST /login（携带 stub-x-token）
curl -i -X POST http://localhost:8080/login \
  -H "Content-Type: application/json" \
  -H "stub-x-token: tester" \
  -d '{"user":"admin"}'

# 预期响应:
# HTTP/1.1 200 OK
# (延迟 500ms 后返回)
```

### 认证 API

```bash
# 登录
 curl -X POST http://localhost:8080/admin/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 预期响应:
# {"code":200,"message":"登录成功","data":{"user":{"id":1,...},"menus":[...],"permissions":["*"]}}

# 获取当前用户
curl http://localhost:8080/admin/api/auth/me \
  -H "Cookie: mock_session_id=xxx"

# 登出
curl -X POST http://localhost:8080/admin/api/auth/logout \
  -H "Cookie: mock_session_id=xxx"
```

### 用户管理 API（需超级管理员权限）

```bash
# 用户列表
curl http://localhost:8080/admin/api/users \
  -H "Cookie: mock_session_id=xxx"

# 创建用户
curl -X POST http://localhost:8080/admin/api/users \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"username":"tester","password":"test123","display_name":"Tester","role_ids":[2]}'

# 更新用户
curl -X PUT http://localhost:8080/admin/api/users/2 \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"display_name":"Updated","is_active":true}'

# 删除用户
curl -X DELETE http://localhost:8080/admin/api/users/2 \
  -H "Cookie: mock_session_id=xxx"
```

### 角色管理 API

```bash
# 角色列表
curl http://localhost:8080/admin/api/roles \
  -H "Cookie: mock_session_id=xxx"

# 创建角色
curl -X POST http://localhost:8080/admin/api/roles \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"name":"开发者","code":"developer"}'

# 获取角色权限
curl http://localhost:8080/admin/api/roles/2/permissions \
  -H "Cookie: mock_session_id=xxx"

# 更新角色权限
curl -X PUT http://localhost:8080/admin/api/roles/2/permissions \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"menu_permissions":[{"menu_id":1,"permissions":["view"]},{"menu_id":2,"permissions":["view","create"]}]}'
```

### 菜单管理 API

```bash
# 菜单树
curl http://localhost:8080/admin/api/menus/tree \
  -H "Cookie: mock_session_id=xxx"

# 创建菜单
curl -X POST http://localhost:8080/admin/api/menus \
  -H "Content-Type: application/json" \
  -H "Cookie: mock_session_id=xxx" \
  -d '{"code":"new_menu","name":"新菜单","path":"/admin/new","sort_order":10}'
```

## Web 管理界面

访问 http://localhost:8080/admin/

默认账号: `admin / admin123`

## WebSocket 测试

```bash
# 使用 websocat 测试回声通道
websocat ws://localhost:8080/ws/echo

# 输入任意消息，服务端会原样返回
```
