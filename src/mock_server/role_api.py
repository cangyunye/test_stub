from aiohttp import web
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from mock_server.db import AsyncSessionLocal
from mock_server.models import Role, Menu, RoleMenu
from mock_server.auth import require_permission


async def role_list_api(request: web.Request):
    """GET /admin/api/roles"""
    await require_permission(request, "roles:view")
    async with AsyncSessionLocal() as session:
        stmt = select(Role).options(selectinload(Role.users), selectinload(Role.menus))
        roles = (await session.execute(stmt)).scalars().all()
        data = []
        for r in roles:
            data.append({
                "id": r.id, "name": r.name, "code": r.code, "is_active": r.is_active,
                "user_count": len(r.users),
                "menus": [m.code for m in r.menus],
            })
    return web.json_response({"code": 200, "message": "success", "data": data})


async def role_create_api(request: web.Request):
    """POST /admin/api/roles"""
    await require_permission(request, "roles:create")
    data = await request.json()
    async with AsyncSessionLocal() as session:
        role = Role(name=data["name"], code=data["code"], is_active=data.get("is_active", True))
        session.add(role)
        await session.commit()
        return web.json_response({"code": 201, "message": "角色创建成功", "data": {"id": role.id}})


async def role_update_api(request: web.Request):
    """PUT /admin/api/roles/{id}"""
    await require_permission(request, "roles:edit")
    role_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        role = await session.get(Role, role_id)
        if not role:
            return web.json_response({"code": 404, "message": "角色不存在", "data": None}, status=404)
        role.name = data.get("name", role.name)
        role.is_active = data.get("is_active", role.is_active)
        await session.commit()
        return web.json_response({"code": 200, "message": "角色更新成功", "data": None})


async def role_delete_api(request: web.Request):
    """DELETE /admin/api/roles/{id}"""
    await require_permission(request, "roles:delete")
    role_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        role = await session.get(Role, role_id)
        if role:
            await session.delete(role)
            await session.commit()
        return web.json_response({"code": 200, "message": "角色删除成功", "data": None})


async def role_permissions_api(request: web.Request):
    """GET /admin/api/roles/{id}/permissions"""
    await require_permission(request, "roles:view")
    role_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        stmt = select(Role).where(Role.id == role_id).options(selectinload(Role.menus))
        role = (await session.execute(stmt)).scalar_one_or_none()
        if not role:
            return web.json_response({"code": 404, "message": "角色不存在", "data": None}, status=404)
        perms = []
        for rm in role.menus:
            role_menu = await session.get(RoleMenu, {"role_id": role.id, "menu_id": rm.id})
            perms.append({"menu_id": rm.id, "menu_code": rm.code, "permissions": role_menu.permissions if role_menu else []})
    return web.json_response({"code": 200, "message": "success", "data": perms})


async def role_permissions_update_api(request: web.Request):
    """PUT /admin/api/roles/{id}/permissions"""
    await require_permission(request, "roles:edit")
    role_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        # 清除旧权限
        await session.execute(RoleMenu.__table__.delete().where(RoleMenu.role_id == role_id))
        for item in data.get("menu_permissions", []):
            session.add(RoleMenu(
                role_id=role_id,
                menu_id=item["menu_id"],
                permissions=item.get("permissions", [])
            ))
        await session.commit()
    return web.json_response({"code": 200, "message": "权限更新成功", "data": None})
