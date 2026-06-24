from aiohttp import web
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from mock_server.db import AsyncSessionLocal
from mock_server.models import User, Role, UserRole
from mock_server.auth import require_permission
import bcrypt


async def user_list_api(request: web.Request):
    """GET /admin/api/users"""
    await require_permission(request, "users:view")
    page = int(request.query.get("page", 1))
    page_size = int(request.query.get("page_size", 20))
    keyword = request.query.get("keyword", "")

    async with AsyncSessionLocal() as session:
        count_stmt = select(func.count(User.id))
        if keyword:
            count_stmt = count_stmt.where((User.username.ilike(f"%{keyword}%")) | (User.display_name.ilike(f"%{keyword}%")))
        total = await session.scalar(count_stmt)

        stmt = select(User).options(selectinload(User.roles))
        if keyword:
            stmt = stmt.where((User.username.ilike(f"%{keyword}%")) | (User.display_name.ilike(f"%{keyword}%")))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        users = (await session.execute(stmt)).scalars().all()

        items = []
        for u in users:
            items.append({
                "id": u.id, "username": u.username, "display_name": u.display_name,
                "is_active": u.is_active, "is_superuser": u.is_superuser,
                "roles": [{"id": r.id, "name": r.name} for r in u.roles],
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            })

    return web.json_response({"code": 200, "message": "success", "data": {"total": total, "page": page, "page_size": page_size, "items": items}})


async def user_create_api(request: web.Request):
    """POST /admin/api/users"""
    await require_permission(request, "users:create")
    data = await request.json()
    async with AsyncSessionLocal() as session:
        user = User(
            username=data["username"],
            password_hash=bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode(),
            display_name=data.get("display_name", ""),
            is_active=data.get("is_active", True),
        )
        session.add(user)
        await session.flush()
        for role_id in data.get("role_ids", []):
            await session.execute(UserRole.__table__.insert().values(user_id=user.id, role_id=role_id))
        await session.commit()
        return web.json_response({"code": 201, "message": "用户创建成功", "data": {"id": user.id, "username": user.username}})


async def user_update_api(request: web.Request):
    """PUT /admin/api/users/{id}"""
    await require_permission(request, "users:edit")
    user_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"code": 404, "message": "用户不存在", "data": None}, status=404)
        user.display_name = data.get("display_name", user.display_name)
        user.is_active = data.get("is_active", user.is_active)
        # 更新角色
        if "role_ids" in data:
            await session.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))
            for role_id in data["role_ids"]:
                await session.execute(UserRole.__table__.insert().values(user_id=user_id, role_id=role_id))
        await session.commit()
        return web.json_response({"code": 200, "message": "用户更新成功", "data": None})


async def user_delete_api(request: web.Request):
    """DELETE /admin/api/users/{id}"""
    await require_permission(request, "users:delete")
    user_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            await session.delete(user)
            await session.commit()
        return web.json_response({"code": 200, "message": "用户删除成功", "data": None})


async def user_reset_password_api(request: web.Request):
    """POST /admin/api/users/{id}/reset-password

    请求体可选：未提供 password 时自动生成随机密码并返回。
    """
    await require_permission(request, "users:edit")
    user_id = int(request.match_info["id"])
    new_password = ""
    try:
        data = await request.json()
    except Exception:
        data = {}
    new_password = data.get("password") or data.get("new_password") or ""
    generated = False
    if not new_password:
        import secrets as _secrets
        new_password = _secrets.token_urlsafe(8)[:10]
        generated = True
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"code": 404, "message": "用户不存在", "data": None}, status=404)
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await session.commit()
        return web.json_response({
            "code": 200, "message": "密码重置成功",
            "data": {"new_password": new_password, "generated": generated},
        })
