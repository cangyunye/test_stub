# Mock Server

基于 Python 3.11 的 HTTP/WebSocket 测试桩（Stub Server），支持多租户端点隔离、Web 管理界面和 ASCII CLI 控制面板。

## 特性

- HTTP + WebSocket 双协议支持
- Jinja2 模板动态响应
- 延迟注入与错误率模拟
- 多租户隔离（`stub-x-token` 请求头）
- Web 管理界面（RBAC 权限控制）
- ASCII CLI 控制面板
- SQLite3 / PostgreSQL 双后端
- 分页、搜索、过滤

## 快速开始

```bash
# 一键启动
./run.sh

# 或手动安装启动
pip install -e ".[dev]"
mock-server start --port 8080
```

访问 http://localhost:8080/admin/，默认账号 `admin / admin123`。

## 预置数据

首次启动自动创建测试用户和端点，无需手动配置即可开始测试：

**用户**

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 超级管理员（全权限） |
| `testuser` | `test123` | 测试人员 |

**Mock 端点（公共）**

```bash
# GET /api/hello — 欢迎消息
curl http://localhost:8080/api/hello

# POST /api/echo — 原样返回
curl -X POST http://localhost:8080/api/echo -d '{"hello":"world"}'

# GET /api/delay — 1 秒延迟
time curl http://localhost:8080/api/delay
```

**Mock 端点（需 `stub-x-token`）**

```bash
# GET /api/admin-only — 仅 admin 可访问
curl http://localhost:8080/api/admin-only -H "stub-x-token: admin"

# POST /api/admin-action
curl -X POST http://localhost:8080/api/admin-action -H "stub-x-token: admin"
```

**WebSocket 回声通道**

```bash
websocat ws://localhost:8080/ws/echo
```

## 文档

| 文档 | 说明 |
|------|------|
| [docs/operations.md](docs/operations.md) | 操作手册（CLI、Web UI、配置、FAQ） |
| [docs/api_examples.md](docs/api_examples.md) | API 使用示例（curl） |
| [AGENTS.md](AGENTS.md) | 开发者/AI 参考（项目结构、命令、约定） |
| [CONTEXT.md](CONTEXT.md) | 领域术语词汇表 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 单文件测试
pytest -xvs tests/test_integration_flow.py
```
