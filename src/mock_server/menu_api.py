from aiohttp import web
from sqlalchemy import select
from mock_server.db import AsyncSessionLocal
from mock_server.models import Menu
from mock_server.auth import require_permission


async def menu_tree_api(request: web.Request):
    """GET /admin/api/menus/tree"""
    await require_permission(request, "menus:view")
    async with AsyncSessionLocal() as session:
        menus = (await session.execute(select(Menu).where(Menu.is_active == True).order_by(Menu.sort_order))).scalars().all()
        menu_map = {m.id: {"id": m.id, "code": m.code, "name": m.name, "path": m.path,
                           "icon": m.icon, "sort_order": m.sort_order, "parent_id": m.parent_id, "children": []} for m in menus}
        roots = []
        for m in menus:
            node = menu_map[m.id]
            if m.parent_id and m.parent_id in menu_map:
                menu_map[m.parent_id]["children"].append(node)
            else:
                roots.append(node)
        roots.sort(key=lambda x: x["sort_order"])
    return web.json_response({"code": 200, "message": "success", "data": roots})


async def menu_create_api(request: web.Request):
    """POST /admin/api/menus"""
    await require_permission(request, "menus:create")
    data = await request.json()
    async with AsyncSessionLocal() as session:
        menu = Menu(
            code=data["code"], name=data["name"], path=data.get("path", ""),
            icon=data.get("icon", ""), parent_id=data.get("parent_id"),
            sort_order=data.get("sort_order", 0), is_active=data.get("is_active", True)
        )
        session.add(menu)
        await session.commit()
        return web.json_response({"code": 201, "message": "菜单创建成功", "data": {"id": menu.id}})


async def menu_update_api(request: web.Request):
    """PUT /admin/api/menus/{id}"""
    await require_permission(request, "menus:edit")
    menu_id = int(request.match_info["id"])
    data = await request.json()
    async with AsyncSessionLocal() as session:
        menu = await session.get(Menu, menu_id)
        if not menu:
            return web.json_response({"code": 404, "message": "菜单不存在", "data": None}, status=404)
        menu.name = data.get("name", menu.name)
        menu.path = data.get("path", menu.path)
        menu.icon = data.get("icon", menu.icon)
        menu.sort_order = data.get("sort_order", menu.sort_order)
        menu.is_active = data.get("is_active", menu.is_active)
        await session.commit()
        return web.json_response({"code": 200, "message": "菜单更新成功", "data": None})


async def menu_delete_api(request: web.Request):
    """DELETE /admin/api/menus/{id}"""
    await require_permission(request, "menus:delete")
    menu_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as session:
        menu = await session.get(Menu, menu_id)
        if menu:
            await session.delete(menu)
            await session.commit()
        return web.json_response({"code": 200, "message": "菜单删除成功", "data": None})
