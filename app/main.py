import asyncio
import logging
import os
import re
import secrets
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app import auth, chat, content_store, events, helper_client, link_settings, live_map, rcon, site_settings, status_cache, world_backends, world_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("zomboid-status")
audit = logging.getLogger("zomboid-status.audit")

APP_DIR = os.path.dirname(__file__)

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET is not set -- generate one (see helper/gen_secrets.py) and put it in .env"
    )
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"

class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app = FastAPI(title="Zomboid Server Status")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=COOKIE_SECURE,
    same_site="lax",
    max_age=auth.SESSION_MAX_AGE_SECONDS,
)
app.mount("/static", NoCacheStaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
app.mount("/icons", NoCacheStaticFiles(directory=link_settings.icons_dir(), check_dir=False), name="icons")
app.mount("/media", NoCacheStaticFiles(directory=content_store.media_dir(), check_dir=False), name="media")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

status_caches: dict[str, status_cache.StatusCache] = {
    slug: status_cache.StatusCache(backend)
    for slug, backend in world_backends.all_backends().items()
}

_CONTROL_CHARS_RE = re.compile(r"[\r\n\x00]")


def _clean(value: str, max_len: int = 200) -> str:
    return _CONTROL_CHARS_RE.sub(" ", (value or "").strip())[:max_len]


def _quote(value: str) -> str:
    escaped = _clean(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _backend_or_404(slug: str) -> world_backends.WorldBackend:
    backend = world_backends.get_backend(slug)
    if backend is None:
        raise HTTPException(status_code=404, detail=f"unknown or not-wired-up world: {slug!r}")
    return backend


def _rcon_for(backend: world_backends.WorldBackend) -> rcon.RconClient:
    return rcon.RconClient(backend.rcon_host, backend.rcon_port, backend.rcon_pass_file)


def _status_dict(s: status_cache.Status) -> dict:
    def iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return {
        "online": s.online,
        "rcon_reachable": s.rcon_reachable,
        "player_count": s.player_count,
        "player_names": s.player_names,
        "mod_state": s.mod_state,
        "last_check_at": iso(s.last_check_at),
        "last_restart_at": iso(s.last_restart_at),
        "last_restart_reason": s.last_restart_reason,
        "next_check_at": iso(s.next_check_at),
        "updated_at": iso(s.updated_at),
        "error": s.error,
        "offline_reason": s.offline_reason,
        "server_info": s.server_info,
        "world_content": s.world_content,
        "join_title": s.join_title,
        "active_event": s.active_event,
        "next_event_name": s.next_event_name,
        "next_event_flavor": s.next_event_flavor,
        "next_event_start_display": s.next_event_start_display,
        "next_event_start_display_simple": s.next_event_start_display_simple,
        "next_event_overridden_early": s.next_event_overridden_early,
        "total_players": s.total_players,
    }


def _tpl(name: str, request: Request, status_code: int = 200, **context):
    context.setdefault("site_settings", site_settings.get_settings())
    context.setdefault("csrf_token", "")
    context.setdefault("is_admin", auth.is_authenticated(request))
    context.setdefault("worlds", world_settings.get_worlds())
    context.setdefault("community_links", link_settings.grouped(link_settings.get_links()))
    return templates.TemplateResponse(
        name, {"request": request, **context}, status_code=status_code
    )


@app.on_event("startup")
async def on_startup():
    for cache in status_caches.values():
        cache.start()


@app.on_event("shutdown")
async def on_shutdown():
    for cache in status_caches.values():
        cache.stop()


@app.get("/")
async def select_world(request: Request):
    return _tpl("select-world.html", request)


@app.get("/world/{slug}")
async def world_view(slug: str, request: Request):
    worlds = world_settings.get_worlds()
    world = next((w for w in worlds if w["slug"] == slug), None)
    if world is None:
        return RedirectResponse("/", status_code=303)

    backend = world_backends.get_backend(slug)
    if backend is not None:
        s = await status_caches[slug].get()
        return _tpl(
            "index.html", request,
            status=_status_dict(s),
            csrf_token=auth.csrf_token(request),
            worlds=worlds,
            world=world,
        )

    return _tpl("world-coming-soon.html", request, worlds=worlds, world=world)


@app.get("/api/{slug}/status")
async def api_status(slug: str):
    _backend_or_404(slug)
    s = await status_caches[slug].get()
    body = _status_dict(s)
    worlds = await asyncio.to_thread(world_settings.get_worlds)
    body["world_label"] = next((w["label"] for w in worlds if w["slug"] == slug), None)
    return JSONResponse(body)


@app.get("/api/{slug}/chat")
async def api_chat(slug: str):
    backend = _backend_or_404(slug)
    messages = await asyncio.to_thread(chat.read_recent, 50, backend.logs_dir)
    return {"messages": messages}


@app.get("/api/{slug}/map/positions")
async def api_map_positions(slug: str):
    backend = _backend_or_404(slug)
    s = await status_caches[slug].get()
    online = set(s.player_names) if s.online else set()
    return await asyncio.to_thread(live_map.read_positions, online, backend.logs_dir)


@app.get("/login")
async def login_form(request: Request):
    if auth.is_authenticated(request):
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse(f"/world/{world_settings.primary_slug()}", status_code=303)


@app.post("/login")
async def login_submit(request: Request):
    ip = client_ip(request)
    primary = world_settings.primary_slug()
    if auth.is_rate_limited(ip):
        return RedirectResponse(f"/world/{primary}?login_error=ratelimited", status_code=303)

    form = await request.form()
    password = form.get("password", "")

    if not auth.verify_password(password):
        auth.record_failed_attempt(ip)
        return RedirectResponse(f"/world/{primary}?login_error=badpass", status_code=303)

    auth.clear_failed_attempts(ip)
    auth.log_in(request)
    return RedirectResponse("/admin", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    auth.log_out(request)
    return RedirectResponse(f"/world/{world_settings.primary_slug()}", status_code=303)


@app.get("/admin", dependencies=[Depends(auth.require_admin_page)])
async def admin_root():
    return RedirectResponse(f"/admin/{world_settings.primary_slug()}", status_code=303)


@app.get("/admin/{slug}", dependencies=[Depends(auth.require_admin_page)])
async def admin_page(slug: str, request: Request):
    backend = _backend_or_404(slug)
    s = await status_caches[slug].get()
    next_event = await asyncio.to_thread(events.read_next, backend.events_dir)
    next_event_is_vacation = bool(next_event) and next_event["script"] == events.VACATION_EVENT
    return _tpl(
        "admin.html",
        request,
        status=_status_dict(s),
        world=next(w for w in world_settings.get_worlds() if w["slug"] == slug),
        wired_slugs=set(status_caches.keys()),
        next_event=next_event,
        next_event_is_vacation=next_event_is_vacation,
        csrf_token=auth.csrf_token(request),
    )


def _require_csrf(request: Request) -> None:
    submitted = request.headers.get("x-csrf-token", "")
    auth.check_csrf(request, submitted)


REBOOT_WARN_THRESHOLD = 4
REBOOT_WARN_SECONDS_SHORT = 30
REBOOT_WARN_SECONDS_LONG = 90
REBOOT_FINAL_WARN_SECONDS = 30


async def _run_admin_reboot(slug: str, rcon_client: rcon.RconClient) -> None:
    try:
        s = await status_caches[slug].get()
        player_count = s.player_count or 0
        if player_count > 0:
            warn = REBOOT_WARN_SECONDS_LONG if player_count > REBOOT_WARN_THRESHOLD else REBOOT_WARN_SECONDS_SHORT
            msg = f"Server restarting in {warn} seconds -- get somewhere safe."
            await asyncio.to_thread(rcon_client.run, f"servermsg {_quote(msg)}")
            if warn > REBOOT_FINAL_WARN_SECONDS:
                await asyncio.sleep(warn - REBOOT_FINAL_WARN_SECONDS)
                final = f"Server restarting in {REBOOT_FINAL_WARN_SECONDS} seconds -- log out somewhere safe now."
                await asyncio.to_thread(rcon_client.run, f"servermsg {_quote(final)}")
                await asyncio.sleep(REBOOT_FINAL_WARN_SECONDS)
            else:
                await asyncio.sleep(warn)
        await asyncio.to_thread(rcon_client.run, "save")
        await asyncio.sleep(15)
        await asyncio.to_thread(rcon_client.run, "quit")
    except rcon.RconError as e:
        log.warning("admin reboot via rcon failed for %s: %s", slug, e)


@app.post("/api/{slug}/admin/reboot", dependencies=[Depends(auth.require_admin_api)])
async def admin_reboot(slug: str, request: Request):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("reboot triggered by %s: %s", client_ip(request), slug)
    asyncio.create_task(_run_admin_reboot(slug, _rcon_for(backend)))
    return {"ok": True, "message": "Restart triggered -- watch the status panel."}


@app.post("/api/{slug}/admin/force-check", dependencies=[Depends(auth.require_admin_api)])
async def admin_force_check(slug: str, request: Request):
    _backend_or_404(slug)
    _require_csrf(request)
    audit.info("force mod-check triggered by %s: %s", client_ip(request), slug)
    try:
        await helper_client.caretaking_status(world=slug)
    except helper_client.HelperError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "message": "Maintenance check triggered (takes ~45s)."}


@app.post("/api/{slug}/admin/event/start-now", dependencies=[Depends(auth.require_admin_api)])
async def admin_start_event_now(slug: str, request: Request):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    next_event = await asyncio.to_thread(events.read_next, backend.events_dir)
    if not next_event:
        raise HTTPException(status_code=400, detail="No event queued to start.")
    script = next_event["script"]
    if script == events.VACATION_EVENT:
        raise HTTPException(status_code=400, detail="The vacation day can't be force-started -- it's on its own automatic schedule.")
    audit.info("start-event-now triggered by %s: %s: %s", client_ip(request), slug, script)
    try:
        await helper_client.event_force(script, world=slug)
    except helper_client.HelperError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "message": f"Starting {next_event['name']} right now -- watch the status panel."}


@app.post("/api/{slug}/admin/event/allow-tonight", dependencies=[Depends(auth.require_admin_api)])
async def admin_event_allow_tonight(slug: str, request: Request):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    next_event = await asyncio.to_thread(events.read_next, backend.events_dir)
    if not next_event:
        raise HTTPException(status_code=400, detail="No event queued.")
    if next_event["script"] == events.VACATION_EVENT:
        raise HTTPException(status_code=400, detail="The vacation day can't be queued early -- it's on its own automatic schedule.")
    audit.info("event-allow-tonight triggered by %s: %s", client_ip(request), slug)
    try:
        await helper_client.event_allow_tonight(world=slug)
    except helper_client.HelperError as e:
        raise HTTPException(status_code=502, detail=str(e))
    try:
        await asyncio.to_thread(events.mark_allow_tonight_override, next_event["script"], backend.content_subdir)
    except OSError as e:
        log.warning("could not record allow-tonight override marker for %s: %s", slug, e)
    await status_caches[slug].refresh_now()
    return {"ok": True, "message": f"Cooldown waived -- {next_event['name']} will start at its normal scheduled time ({next_event['start_display']})."}


class BroadcastBody(BaseModel):
    message: str


@app.post("/api/{slug}/admin/broadcast", dependencies=[Depends(auth.require_admin_api)])
async def admin_broadcast(slug: str, request: Request, body: BroadcastBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("broadcast by %s: %s: %r", client_ip(request), slug, body.message)
    out = await asyncio_to_thread_run(_rcon_for(backend), f"servermsg {_quote(body.message)}")
    return {"ok": True, "output": out}


@app.post("/api/{slug}/admin/save", dependencies=[Depends(auth.require_admin_api)])
async def admin_save(slug: str, request: Request):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("manual save by %s: %s", client_ip(request), slug)
    out = await asyncio_to_thread_run(_rcon_for(backend), "save")
    return {"ok": True, "output": out}


class UsernameBody(BaseModel):
    username: str


@app.post("/api/{slug}/admin/kick", dependencies=[Depends(auth.require_admin_api)])
async def admin_kick(slug: str, request: Request, body: UsernameBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("kick by %s: %s: %r", client_ip(request), slug, body.username)
    out = await asyncio_to_thread_run(_rcon_for(backend), f"kickuser {_quote(body.username)}")
    return {"ok": True, "output": out}


class BanBody(BaseModel):
    username: str
    ip_ban: bool = False
    reason: str = ""


@app.post("/api/{slug}/admin/ban", dependencies=[Depends(auth.require_admin_api)])
async def admin_ban(slug: str, request: Request, body: BanBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("ban by %s: %s: %r ip=%s reason=%r", client_ip(request), slug, body.username, body.ip_ban, body.reason)
    cmd = f"banuser {_quote(body.username)}"
    if body.ip_ban:
        cmd += " -ip"
    if body.reason:
        cmd += f" -r {_quote(body.reason)}"
    out = await asyncio_to_thread_run(_rcon_for(backend), cmd)
    return {"ok": True, "output": out}


class WhitelistAddBody(BaseModel):
    username: str
    password: str | None = None


@app.post("/api/{slug}/admin/whitelist/add", dependencies=[Depends(auth.require_admin_api)])
async def admin_whitelist_add(slug: str, request: Request, body: WhitelistAddBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    password = body.password or secrets.token_urlsafe(9)
    audit.info("whitelist add by %s: %s: %r", client_ip(request), slug, body.username)
    out = await asyncio_to_thread_run(_rcon_for(backend), f"adduser {_quote(body.username)} {_quote(password)}")
    return {
        "ok": True,
        "output": out,
        "message": f"Added {body.username} to whitelist. Password: {password}",
    }


@app.post("/api/{slug}/admin/whitelist/remove", dependencies=[Depends(auth.require_admin_api)])
async def admin_whitelist_remove(slug: str, request: Request, body: UsernameBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("whitelist remove by %s: %s: %r", client_ip(request), slug, body.username)
    out = await asyncio_to_thread_run(_rcon_for(backend), f"removeuserfromwhitelist {_quote(body.username)}")
    return {"ok": True, "output": out}


class TeleportBody(BaseModel):
    username: str
    to_username: str


@app.post("/api/{slug}/admin/teleport", dependencies=[Depends(auth.require_admin_api)])
async def admin_teleport(slug: str, request: Request, body: TeleportBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    audit.info("teleport by %s: %s: %r -> %r", client_ip(request), slug, body.username, body.to_username)
    out = await asyncio_to_thread_run(_rcon_for(backend), f"teleport {_quote(body.username)} {_quote(body.to_username)}")
    return {"ok": True, "output": out, "message": f"Teleported {body.username} to {body.to_username}."}


CONTENT_KEYS = {"patchnotes", "lore", "faq", "join_title"}
MAX_CONTENT_CHARS = 20000


class ContentBody(BaseModel):
    text: str


@app.get("/api/{slug}/admin/content/{key}", dependencies=[Depends(auth.require_admin_api)])
async def admin_get_content(slug: str, key: str):
    backend = _backend_or_404(slug)
    if key not in CONTENT_KEYS:
        raise HTTPException(status_code=404, detail="unknown content key")
    return await asyncio.to_thread(content_store.get_raw, key, backend.content_subdir)


@app.post("/api/{slug}/admin/content/{key}", dependencies=[Depends(auth.require_admin_api)])
async def admin_save_content(slug: str, key: str, request: Request, body: ContentBody):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    if key not in CONTENT_KEYS:
        raise HTTPException(status_code=404, detail="unknown content key")
    if len(body.text) > MAX_CONTENT_CHARS:
        raise HTTPException(status_code=400, detail=f"text too long ({MAX_CONTENT_CHARS} char max)")
    audit.info("content edit by %s: %s: %s (%d chars)", client_ip(request), slug, key, len(body.text))
    await asyncio.to_thread(content_store.save_raw, key, body.text, backend.content_subdir)
    await status_caches[slug].refresh_now()
    return {"ok": True}


@app.post("/api/{slug}/admin/content/{key}/revert", dependencies=[Depends(auth.require_admin_api)])
async def admin_revert_content(slug: str, key: str, request: Request):
    backend = _backend_or_404(slug)
    _require_csrf(request)
    if key not in CONTENT_KEYS:
        raise HTTPException(status_code=404, detail="unknown content key")
    audit.info("content revert by %s: %s: %s", client_ip(request), slug, key)
    await asyncio.to_thread(content_store.revert, key, backend.content_subdir)
    await status_caches[slug].refresh_now()
    return {"ok": True}


@app.get("/api/admin/settings", dependencies=[Depends(auth.require_admin_api)])
async def admin_get_settings():
    return await asyncio.to_thread(site_settings.get_settings)


class SettingsBody(BaseModel):
    brand_title: str | None = None
    brand_subtitle_text: str | None = None
    brand_subtitle_url: str | None = None
    section_join: str | None = None
    section_news: str | None = None
    section_lore: str | None = None


@app.post("/api/admin/settings", dependencies=[Depends(auth.require_admin_api)])
async def admin_save_settings(request: Request, body: SettingsBody):
    _require_csrf(request)
    partial = {k: v for k, v in body.model_dump().items() if v is not None}
    audit.info("settings edit by %s: %s", client_ip(request), list(partial))
    return await asyncio.to_thread(site_settings.save_settings, partial)


@app.get("/api/admin/worlds", dependencies=[Depends(auth.require_admin_api)])
async def admin_get_worlds():
    return await asyncio.to_thread(world_settings.get_worlds)


class WorldEntry(BaseModel):
    slug: str
    label: str
    color: str
    primary: bool = False
    image: str = ""


class WorldsBody(BaseModel):
    worlds: list[WorldEntry]


@app.post("/api/admin/worlds", dependencies=[Depends(auth.require_admin_api)])
async def admin_save_worlds(request: Request, body: WorldsBody):
    _require_csrf(request)
    audit.info("worlds edit by %s: %d world(s)", client_ip(request), len(body.worlds))
    try:
        return await asyncio.to_thread(
            world_settings.save_worlds, [w.model_dump() for w in body.worlds]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/admin/links", dependencies=[Depends(auth.require_admin_api)])
async def admin_get_links():
    return await asyncio.to_thread(link_settings.get_links)


class LinkEntry(BaseModel):
    label: str
    url: str
    color: str
    group: str
    icon: str = ""


class LinksBody(BaseModel):
    links: list[LinkEntry]


@app.post("/api/admin/links", dependencies=[Depends(auth.require_admin_api)])
async def admin_save_links(request: Request, body: LinksBody):
    _require_csrf(request)
    audit.info("links edit by %s: %d link(s)", client_ip(request), len(body.links))
    try:
        return await asyncio.to_thread(
            link_settings.save_links, [e.model_dump() for e in body.links]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def asyncio_to_thread_run(rcon_client: rcon.RconClient, command: str) -> str:
    try:
        return await asyncio.to_thread(rcon_client.run, command)
    except rcon.RconError as e:
        raise HTTPException(status_code=502, detail=f"RCON error: {e}")
