import asyncio
import click
from aiohttp import web
from sqlalchemy import select, desc, func
from mock_server.db import AsyncSessionLocal, engine
from mock_server.models import Endpoint, RequestLog, WebSocketChannel, User
from mock_server.server import create_app
from mock_server.config import settings


@click.group()
def main():
    """Mock Server Control Panel"""
    pass


@main.command()
@click.option("--host", default=settings.host, help="Bind host")
@click.option("--port", default=settings.port, help="Bind port")
def start(host, port):
    """Start the mock server"""
    click.echo(f"Starting Mock Server on {host}:{port} ...")
    app = create_app()
    web.run_app(app, host=host, port=port)


@main.command()
def status():
    """Show server status panel (ASCII)"""
    async def _show():
        async with AsyncSessionLocal() as session:
            ep_count = await session.scalar(select(func.count()).select_from(Endpoint))
            ws_count = await session.scalar(select(func.count()).select_from(WebSocketChannel))
            req_count = await session.scalar(select(func.count()).select_from(RequestLog))
            recent = (await session.execute(
                select(RequestLog).order_by(desc(RequestLog.created_at)).limit(5)
            )).scalars().all()

        click.echo("+" + "="*74 + "+")
        click.echo("|" + " MOCK SERVER CONTROL PANEL v1.0".center(74) + "|")
        click.echo("+" + "="*74 + "+")
        click.echo(f"|  Endpoints: {ep_count:<4}  WS Channels: {ws_count:<4}  Total Requests: {req_count:<8}  |")
        click.echo("+" + "-"*74 + "+")
        click.echo("|  LAST 5 REQUESTS" + " "*57 + "|")
        click.echo("+--------+----------+----------------------+----------+--------------------+")
        click.echo("|  TIME  | METHOD   | PATH                 | STATUS   | DURATION           |")
        click.echo("+--------+----------+----------------------+----------+--------------------+")
        for log in recent:
            t = log.created_at.strftime('%H:%M') if log.created_at else '--:--'
            click.echo(f"| {t:<6} | {log.method:<8} | {log.path:<20} | {log.response_status or '-':<8} | {log.duration_ms:<4}ms{' '*11} |")
        click.echo("+" + "="*74 + "+")

    asyncio.run(_show())


@main.command()
@click.option("--method", default="GET", help="HTTP method")
@click.option("--path", required=True, help="Route path")
@click.option("--status", default=200, help="Response status code")
@click.option("--body", default='{"ok": true}', help="Response body")
@click.option("--delay", default=0, help="Delay in ms")
@click.option("--error-rate", default=0.0, help="Error rate 0.0-1.0")
@click.option("--owner", default=None, help="Owner username (user-specific endpoint)")
@click.option("--public", is_flag=True, help="Create public endpoint (no owner)")
def add_endpoint(method, path, status, body, delay, error_rate, owner, public):
    """Add a new HTTP mock endpoint"""
    async def _add():
        async with AsyncSessionLocal() as session:
            owner_id = None
            if owner and not public:
                stmt = select(User).where(User.username == owner)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if user:
                    owner_id = user.id
                else:
                    click.echo(f"[WARN] User '{owner}' not found, creating public endpoint")
            ep = Endpoint(
                owner_id=owner_id,
                method=method.upper(),
                path=path,
                status_code=status,
                response_body=body,
                delay_ms=delay,
                error_rate=error_rate,
            )
            session.add(ep)
            await session.commit()
            scope = "public" if owner_id is None else f"owner={owner}"
            click.echo(f"[OK] Endpoint {method.upper()} {path} -> {status} ({scope})")
    asyncio.run(_add())


@main.command()
@click.option("--path", required=True, help="WebSocket path")
@click.option("--template", default='{"msg": "hello"}', help="Message template")
@click.option("--interval", default=0, help="Auto push interval (seconds)")
@click.option("--echo/--no-echo", default=False, help="Echo mode")
def add_ws(path, template, interval, echo):
    """Add a new WebSocket channel"""
    async def _add():
        async with AsyncSessionLocal() as session:
            ch = WebSocketChannel(
                path=path,
                message_template=template,
                auto_push_interval=interval,
                echo_mode=echo,
            )
            session.add(ch)
            await session.commit()
            click.echo(f"[OK] WebSocket channel {path}")
    asyncio.run(_add())


@main.command()
def list_endpoints():
    """List all HTTP endpoints"""
    async def _list():
        async with AsyncSessionLocal() as session:
            endpoints = (await session.execute(select(Endpoint))).scalars().all()
        click.echo("+--------+----------+--------+----------+-------+----------+")
        click.echo("| METHOD | PATH     | STATUS | DELAY    | ERROR | SCOPE    |")
        click.echo("+--------+----------+--------+----------+-------+----------+")
        for ep in endpoints:
            scope = "public" if ep.owner_id is None else f"user#{ep.owner_id}"
            click.echo(f"| {ep.method:<6} | {ep.path:<8} | {ep.status_code:<6} | {ep.delay_ms:<4}ms{' '*3} | {ep.error_rate:<5.2f} | {scope:<8} |")
        click.echo("+--------+----------+--------+----------+-------+----------+")
    asyncio.run(_list())


@main.command()
@click.confirmation_option(prompt="Are you sure you want to clear all logs?")
def clear_logs():
    """Clear all request logs"""
    async def _clear():
        async with AsyncSessionLocal() as session:
            await session.execute(RequestLog.__table__.delete())
            await session.commit()
            click.echo("[OK] All logs cleared")
    asyncio.run(_clear())


if __name__ == "__main__":
    main()
