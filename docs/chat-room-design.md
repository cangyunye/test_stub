# WebSocket 聊天室设计计划（搁置）

## 目标
在 `/chat` 路径提供一个简易 WebSocket 聊天室，支持：
- 用户身份识别（基于现有登录 session）
- 消息广播（全体在线用户）
- 消息格式：发送者、时间戳、内容
- 管理员可通过现有 WS 管理界面开关聊天室

## 架构

```
浏览器 WS 连接 ws://host/chat
  ↓
chat_handler（新文件 chat.py）
  ├─ 1. 读取 Cookie → SESSION_STORE 查用户
  ├─ 2. 查 WebSocketChannel 表 /chat 行 → is_active?
  ├─ 3. 加入广播池 _connected（内存 Set）
  ├─ 4. 消息流转: {type, user, text, timestamp} → 广播全体
  └─ 5. 断开 → 广播离开消息
```

## 改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/mock_server/chat.py` | 新增 | 聊天室 handler，含广播池 + 鉴权 + 消息路由 |
| `src/mock_server/server.py` | 修改 | `on_startup` 中注册 `/chat` 路由（在 catch-all 之前） |
| `src/mock_server/websocket.py` | 修改 | `register_websocket_routes` 过滤掉 `path == "/chat"` |
| `src/mock_server/seed.py` | 修改 | 新增 `WebSocketChannel(path="/chat", is_active=True)` 种子数据 |
| `src/mock_server/static/chat.html` | 新增 | 聊天室前端页面，登录态校验 + WS 消息收发 |
| `src/mock_server/admin_pages.py` | 修改 | 注册 `chat.html` 到页面缓存 |
| `src/mock_server/admin_routes.py` | 修改 | 添加 `/admin/chat.html` 路由 |

## 关键设计决策

- **用户识别**：WS 握手时读取 `mock_session_id` cookie，查 `SESSION_STORE` 取用户信息。未登录 → `close(4001)`
- **消息格式**：
  - 用户消息: `{"type":"message", "user":{"id","username","display_name"}, "text":"...", "timestamp":"..."}`
  - 系统消息: `{"type":"system", "text":"... 进入了/离开了聊天室", "timestamp":"..."}`
- **广播**：`asyncio.Lock` + `set[WebSocketResponse]`，收到消息发给全部连接（含发送者自身）
- **管理员关闭**：在已有 WS 管理页面 toggle `/chat` 的 `is_active`。新连接检查 DB，disabled 则 `close(1008)`
- **历史消息**：不持久化，不保留
- **前端**：独立 `chat.html`，匹配现有暗色主题，登录态校验后连接 WS

## 待确认

1. 前端位置：`/chat.html`（独立，handler 自鉴权）vs `/admin/chat.html`（走现有 admin 中间件）
2. 侧边栏是否加"聊天室"入口
