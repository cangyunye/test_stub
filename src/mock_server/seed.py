import bcrypt
from sqlalchemy import select
from mock_server.db import AsyncSessionLocal
from mock_server.models import User, Role, Menu, Endpoint, WebSocketChannel, UserRole, RoleMenu


async def seed_data():
    async with AsyncSessionLocal() as session:
        # 检查是否已有数据
        existing = await session.scalar(select(User).where(User.username == "admin"))
        if existing:
            return

        # 创建默认角色
        superadmin = Role(name="超级管理员", code="superadmin", is_active=True)
        tester = Role(name="测试人员", code="tester", is_active=True)
        readonly = Role(name="只读用户", code="readonly", is_active=True)
        session.add_all([superadmin, tester, readonly])
        await session.flush()

        # 创建默认菜单
        menus_data = [
            ("dashboard", "Dashboard", "/admin/", "dashboard", None, 1),
            ("endpoints", "Endpoints", "/admin/endpoints", "api", None, 2),
            ("endpoints_list", "List", "/admin/endpoints", "list", 2, 1),
            ("endpoints_add", "Add", "/admin/endpoints/new", "plus", 2, 2),
            ("websockets", "WebSockets", "/admin/websocket-channels", "websocket", None, 3),
            ("ws_list", "List", "/admin/websocket-channels", "list", 5, 1),
            ("ws_add", "Add", "/admin/websocket-channels/new", "plus", 5, 2),
            ("logs", "Logs", "/admin/logs", "file-text", None, 4),
            ("settings", "Settings", "/admin/settings", "settings", None, 5),
            ("users", "Users", "/admin/settings/users", "users", 9, 1),
            ("roles", "Roles", "/admin/settings/roles", "shield", 9, 2),
            ("menus", "Menus", "/admin/settings/menus", "menu", 9, 3),
            ("config", "Config", "/admin/settings/config", "sliders", 9, 4),
        ]
        menu_objs = {}
        for code, name, path, icon, parent_id, sort in menus_data:
            m = Menu(code=code, name=name, path=path, icon=icon, parent_id=parent_id, sort_order=sort, is_active=True)
            session.add(m)
            await session.flush()
            menu_objs[code] = m

        # 超级管理员拥有所有权限
        for m in menu_objs.values():
            session.add(RoleMenu(role_id=superadmin.id, menu_id=m.id, permissions=["view", "create", "edit", "delete"]))

        # 测试人员权限
        tester_menus = ["dashboard", "endpoints", "endpoints_list", "endpoints_add", "websockets", "ws_list", "ws_add", "logs"]
        for code in tester_menus:
            perms = ["view", "create", "edit"] if code in ("endpoints", "websockets") else ["view"]
            session.add(RoleMenu(role_id=tester.id, menu_id=menu_objs[code].id, permissions=perms))

        # 只读用户权限
        readonly_menus = ["dashboard", "endpoints", "endpoints_list", "websockets", "ws_list", "logs"]
        for code in readonly_menus:
            session.add(RoleMenu(role_id=readonly.id, menu_id=menu_objs[code].id, permissions=["view"]))

        # 创建默认管理员
        admin = User(
            username="admin",
            password_hash=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
            display_name="系统管理员",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.flush()
        session.add(UserRole(user_id=admin.id, role_id=superadmin.id))
        await session.flush()

        # 创建测试用户 tester（归属测试人员角色）
        testuser = User(
            username="testuser",
            password_hash=bcrypt.hashpw("test123".encode(), bcrypt.gensalt()).decode(),
            display_name="测试用户",
            is_active=True,
            is_superuser=False,
        )
        session.add(testuser)
        await session.flush()
        session.add(UserRole(user_id=testuser.id, role_id=tester.id))

        # 创建示例公共端点
        endpoints = [
            Endpoint(method="GET", path="/api/hello", status_code=200,
                     response_body='{"message": "Hello from Mock Server!", "timestamp": "{{ headers.Host }}"}',
                     owner_id=None, is_active=True),
            Endpoint(method="POST", path="/api/echo", status_code=200,
                     response_body='{{ body }}',
                     content_type="application/json", owner_id=None, is_active=True),
            Endpoint(method="GET", path="/api/delay", status_code=200,
                     response_body='{"slow": true}',
                     delay_ms=1000, owner_id=None, is_active=True),
        ]
        session.add_all(endpoints)

        # 创建示例用户专属端点（归 admin）
        owner_endpoints = [
            Endpoint(method="GET", path="/api/admin-only", status_code=200,
                     response_body='{"secret": "this is admin-only data"}',
                     owner_id=admin.id, is_active=True),
            Endpoint(method="POST", path="/api/admin-action", status_code=200,
                     response_body='{"action": "done", "user": "{{ headers.stub-x-token }}"}',
                     owner_id=admin.id, is_active=True),
        ]
        session.add_all(owner_endpoints)

        # 创建示例 WebSocket 回声通道
        ws = WebSocketChannel(
            path="/ws/echo",
            echo_mode=True,
            is_active=True,
        )
        session.add(ws)

        await session.commit()
