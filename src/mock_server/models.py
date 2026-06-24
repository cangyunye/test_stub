from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from mock_server.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    response_body: Mapped[str] = mapped_column(Text, default="{}")
    response_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    content_type: Mapped[str] = mapped_column(String(100), default="application/json")
    delay_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    condition_rules: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="endpoints")
    logs: Mapped[list["RequestLog"]] = relationship("RequestLog", back_populates="endpoint")


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    query_params: Mapped[dict] = mapped_column(JSON, default=dict)
    request_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    request_body: Mapped[str] = mapped_column(Text, default="")
    response_status: Mapped[int] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    client_ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    endpoint: Mapped["Endpoint"] = relationship("Endpoint", back_populates="logs")


class WebSocketChannel(Base):
    __tablename__ = "websocket_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    message_template: Mapped[str] = mapped_column(Text, default="{}")
    auto_push_interval: Mapped[int] = mapped_column(Integer, default=0)
    echo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", back_populates="users")
    endpoints: Mapped[list["Endpoint"]] = relationship("Endpoint", back_populates="owner")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship("User", secondary="user_roles", back_populates="roles")
    menus: Mapped[list["Menu"]] = relationship("Menu", secondary="role_menus", back_populates="roles")


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(200), default="")
    icon: Mapped[str] = mapped_column(String(50), default="")
    parent_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    children: Mapped[list["Menu"]] = relationship("Menu", remote_side="Menu.id", backref="parent")
    roles: Mapped[list["Role"]] = relationship("Role", secondary="role_menus", back_populates="menus")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)


class RoleMenu(Base):
    __tablename__ = "role_menus"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
