# Mock Server — Domain Glossary

> 项目语境总览，仅记录领域术语。不包含实现细节。

## Mock Server（服务桩）

为外部被测系统提供预设 HTTP/WebSocket 响应的独立进程。与单元测试中的 Mock 不同，它是一个真实的网络服务，不拦截调用，而是监听端口并按照预设规则回复。

**本质分类：** 响应预设型 Stub（Response-Preset Stub）

**关键特征：**
- 预先配置路由规则、响应内容、延迟、错误率
- 支持 Jinja2 模板动态渲染响应体
- 支持条件规则分支（根据请求参数返回不同响应）
- 记录所有请求日志，可事后查询，但不做自动断言
- 外部测试代码负责断言（请求后自行校验返回结果）

## Endpoint（端点）

一条 HTTP Mock 路由规则，包含方法、路径、响应状态码、响应体、延迟、错误率、条件规则等配置。

**归属隔离：** 每个端点归属于一个 `owner_id`（用户 ID）。请求时通过请求头 `stub-x-token` 识别调用者身份，仅匹配该用户注册的端点。无 `stub-x-token` 的请求命中公共端点（`owner_id IS NULL`）。

### Condition Rule（条件规则）

端点中用于分支响应的匹配规则。当前版本仅支持 **单层 key=value 精确匹配**（如 `{"method": "POST", "query.type": "vip"}`），通过 `request_data.get(key)` 逐条比对。

## WebSocketChannel（WebSocket 通道）

一条 WebSocket Mock 路由规则，支持回声模式、自动推送、消息模板三种响应模式。

## RequestLog（请求日志）

每次经过 Mock Server 的请求记录，包含请求头、请求体、响应状态、响应体、耗时等。

## Stub Token（桩标识）

请求头 `stub-x-token` 的值，用于标识 Mock 端点的调用者身份。服务端通过该 token 查找对应的 `User`，进而匹配该用户专属的 `Endpoint`。无此请求头时命中公共端点（`owner_id IS NULL`）。

## RBAC（基于角色的访问控制）

Admin 管理界面的权限模型。用户绑定角色，角色绑定菜单和操作权限（view/create/edit/delete），超级管理员拥有所有权限不受限。

## Session（会话）

Admin 用户登录后在服务端内存中的状态存储，通过 Cookie `mock_session_id` 传递，TTL 1 小时。
