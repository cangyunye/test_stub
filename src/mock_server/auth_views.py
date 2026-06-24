import bcrypt
from aiohttp import web
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from mock_server.db import AsyncSessionLocal
from mock_server.models import User, Role, Menu, RoleMenu
from mock_server.auth import create_session, destroy_session, USER_KEY


async def login_api(request: web.Request):
    """登录 API POST /admin/api/auth/login"""
    is_form = request.content_type == "application/x-www-form-urlencoded"
    data = await request.post() if is_form else await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    remember_me = data.get("remember_me", False)

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.username == username, User.is_active == True).options(
            selectinload(User.roles).selectinload(Role.menus)
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            if is_form:
                raise web.HTTPFound("/admin/login")
            return web.json_response({"code": 401, "message": "用户名或密码错误", "data": None}, status=401)

        # 查询用户权限
        permissions = []
        menus = []
        if user.is_superuser:
            permissions = ["*"]
            menu_stmt = select(Menu).where(Menu.is_active == True).order_by(Menu.sort_order)
            menus = (await session.execute(menu_stmt)).scalars().all()
        else:
            for role in user.roles:
                for rm in role.menus:
                    if rm.is_active:
                        menus.append(rm)
                        role_menu = await session.get(RoleMenu, {"role_id": role.id, "menu_id": rm.id})
                        if role_menu:
                            for perm in role_menu.permissions:
                                permissions.append(f"{rm.code}:{perm}")

        # 去重菜单
        seen = set()
        unique_menus = []
        for m in menus:
            if m.id not in seen:
                seen.add(m.id)
                unique_menus.append(m)

        # 构建菜单树
        menu_tree = _build_menu_tree(unique_menus)

        user_data = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_superuser": user.is_superuser,
        }

        session_id = create_session(user_data, permissions)

        # 更新最后登录时间
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()

        if is_form:
            response = web.HTTPFound("/admin/")
            max_age = 86400 * 7 if remember_me else None
            response.set_cookie("mock_session_id", session_id, httponly=True, max_age=max_age, path="/")
            raise response
        else:
            response = web.json_response({
                "code": 200,
                "message": "登录成功",
                "data": {
                    "user": user_data,
                    "menus": menu_tree,
                    "permissions": permissions,
                }
            })
            max_age = 86400 * 7 if remember_me else None
            response.set_cookie("mock_session_id", session_id, httponly=True, max_age=max_age, path="/")
            return response


async def logout_api(request: web.Request):
    """登出 API POST /admin/api/auth/logout"""
    session_id = request.cookies.get("mock_session_id")
    if session_id:
        destroy_session(session_id)
    response = web.json_response({"code": 200, "message": "登出成功", "data": None})
    response.del_cookie("mock_session_id", path="/")
    return response


async def me_api(request: web.Request):
    """当前用户 GET /admin/api/auth/me"""
    user_data = request.get(USER_KEY)
    if not user_data:
        return web.json_response({"code": 401, "message": "未登录", "data": None}, status=401)
    return web.json_response({"code": 200, "message": "success", "data": user_data})


async def change_password_api(request: web.Request):
    """修改密码 POST /admin/api/auth/change-password"""
    user_data = request.get(USER_KEY)
    if not user_data:
        return web.json_response({"code": 401, "message": "未登录", "data": None}, status=401)

    data = await request.json()
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")
    confirm_pw = data.get("confirm_password", "")

    if new_pw != confirm_pw:
        return web.json_response({"code": 400, "message": "新密码与确认密码不一致", "data": None}, status=400)

    async with AsyncSessionLocal() as session:
        db_user = await session.get(User, user_data["id"])
        if not bcrypt.checkpw(old_pw.encode(), db_user.password_hash.encode()):
            return web.json_response({"code": 400, "message": "原密码错误", "data": None}, status=400)

        db_user.password_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
        await session.commit()

    return web.json_response({"code": 200, "message": "密码修改成功", "data": None})


def _build_menu_tree(menus: list) -> list:
    """构建菜单树结构"""
    menu_map = {m.id: {"id": m.id, "code": m.code, "name": m.name, "path": m.path,
                       "icon": m.icon, "sort_order": m.sort_order, "children": []} for m in menus}
    roots = []
    for m in menus:
        node = menu_map[m.id]
        if m.parent_id and m.parent_id in menu_map:
            menu_map[m.parent_id]["children"].append(node)
        else:
            roots.append(node)
    roots.sort(key=lambda x: x["sort_order"])
    return roots
