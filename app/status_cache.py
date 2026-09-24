import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from app import content_store, events, helper_client, player_db, rcon, schedule, server_info
from app.world_backends import WorldBackend

log = logging.getLogger("zomboid-status")

REFRESH_INTERVAL_SECONDS = 20

_LOG_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})  (.*)$")
_RUN_START_RE = re.compile(r"=== run start \(dry_run=\w+ force=(true|false)\) ===")

_DOCKER_STATE_RE = re.compile(r"^(true|false)\s+(\S+)$", re.IGNORECASE)


def _parse_docker_state(state: str) -> tuple[bool | None, datetime | None]:
    m = _DOCKER_STATE_RE.match(state.strip())
    if not m:
        return None, None
    running = m.group(1).lower() == "true"
    ts = re.sub(r"\.(\d{1,6})\d*Z$", r".\1+00:00", m.group(2))
    ts = re.sub(r"Z$", "+00:00", ts)
    try:
        started_at = datetime.fromisoformat(ts).astimezone(events.EVENT_TZ).replace(tzinfo=None)
    except ValueError:
        started_at = None
    return running, started_at


_NIGHTLY_MAINTENANCE_START = time(0, 45)
_NIGHTLY_MAINTENANCE_END = time(1, 15)


def _nightly_maintenance_reason(restart_at: datetime) -> str | None:
    if _NIGHTLY_MAINTENANCE_START <= restart_at.time() <= _NIGHTLY_MAINTENANCE_END:
        return "nightly maintenance restarted it"
    return None


@dataclass
class Status:
    online: bool = False
    rcon_reachable: bool = False
    player_count: int = 0
    player_names: list[str] = field(default_factory=list)
    mod_state: str = "unknown"
    last_check_at: datetime | None = None
    last_restart_at: datetime | None = None
    last_restart_reason: str | None = None
    next_check_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None
    offline_reason: str | None = None
    server_info: dict = field(default_factory=dict)
    world_content: dict = field(default_factory=dict)
    join_title: str = "Join the server"
    active_event: dict | None = None
    next_event_name: str | None = None
    next_event_flavor: str | None = None
    next_event_start_display: str | None = None
    next_event_start_display_simple: str | None = None
    next_event_overridden_early: bool = False
    total_players: int | None = None


def _parse_caretaking_log(path: str) -> tuple[str, datetime | None, datetime | None, str | None]:
    if not os.path.exists(path):
        return "never-checked", None, None, None

    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        log.warning("could not read caretaking log %s: %s", path, e)
        return "unknown", None, None, None

    mod_state = "never-checked"
    last_check_at: datetime | None = None
    last_restart_at: datetime | None = None
    last_restart_reason: str | None = None
    seeking_restart_reason = False

    for line in reversed(lines):
        m = _LOG_LINE_RE.match(line.rstrip("\n"))
        if not m:
            continue
        ts_str, message = m.group(1), m.group(2)

        if last_check_at is None and message.startswith("mod state:"):
            state = message.split(":", 1)[1].strip()
            if state in ("fresh", "stale", "unknown"):
                mod_state = state
                try:
                    last_check_at = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        if last_restart_at is None and "run complete: restarted successfully" in message:
            try:
                last_restart_at = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                seeking_restart_reason = True
            except ValueError:
                pass

        if last_restart_at is None and "run complete: recovered from a crashed server process" in message:
            try:
                last_restart_at = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                last_restart_reason = "the server crashed"
            except ValueError:
                pass

        if seeking_restart_reason:
            run_start = _RUN_START_RE.search(message)
            if run_start:
                forced = run_start.group(1) == "true"
                last_restart_reason = "an admin restarted it manually" if forced else "mod updates were found"
                seeking_restart_reason = False

        if last_check_at is not None and last_restart_at is not None and not seeking_restart_reason:
            break

    return mod_state, last_check_at, last_restart_at, last_restart_reason


class StatusCache:
    def __init__(self, backend: WorldBackend):
        self._backend = backend
        self._status = Status()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    async def get(self) -> Status:
        async with self._lock:
            return self._status

    async def refresh_now(self) -> None:
        await self._refresh_once()

    async def _refresh_once(self) -> None:
        backend = self._backend
        rcon_client = rcon.RconClient(backend.rcon_host, backend.rcon_port, backend.rcon_pass_file)

        new_status = Status(updated_at=datetime.now())
        new_status.next_check_at = schedule.next_check_time(datetime.now())

        mod_state, last_check_at, log_restart_at, log_restart_reason = await asyncio.to_thread(
            _parse_caretaking_log, backend.caretaking_log
        )
        new_status.mod_state = mod_state
        new_status.last_check_at = last_check_at

        try:
            docker_running, container_started_at = _parse_docker_state(
                await helper_client.docker_state(world=backend.slug)
            )
        except helper_client.HelperError:
            docker_running, container_started_at = None, None

        if container_started_at is not None:
            new_status.last_restart_at = container_started_at
            if log_restart_at is not None and abs(log_restart_at - container_started_at) < timedelta(minutes=5):
                new_status.last_restart_reason = log_restart_reason
            else:
                new_status.last_restart_reason = None
        else:
            new_status.last_restart_at = log_restart_at
            new_status.last_restart_reason = log_restart_reason

        if new_status.last_restart_reason is None and new_status.last_restart_at is not None:
            new_status.last_restart_reason = _nightly_maintenance_reason(new_status.last_restart_at)

        new_status.server_info = await asyncio.to_thread(server_info.read_server_info, backend.server_ini)
        new_status.world_content = await asyncio.to_thread(content_store.get_world_content, backend.content_subdir)
        join_title = await asyncio.to_thread(content_store.get_plain, "join_title", backend.content_subdir)
        new_status.join_title = join_title or "Join the server"
        new_status.active_event = await asyncio.to_thread(events.read_active, backend.events_dir)
        next_event = await asyncio.to_thread(events.read_next, backend.events_dir)
        new_status.next_event_name = next_event["name"] if next_event else None
        new_status.next_event_flavor = next_event["flavor"] if next_event else None
        new_status.next_event_start_display = next_event["start_display"] if next_event else None
        new_status.next_event_start_display_simple = next_event["start_display_simple"] if next_event else None
        new_status.next_event_overridden_early = bool(next_event and next_event["overridden_early"])
        new_status.total_players = await asyncio.to_thread(player_db.total_players, backend.player_db)

        try:
            players_out = await asyncio.to_thread(rcon_client.run, "players")
            new_status.rcon_reachable = True
            new_status.online = True
            new_status.player_count = rcon.parse_player_count(players_out)
            new_status.player_names = rcon.parse_player_names(players_out)
        except rcon.RconError as e:
            new_status.rcon_reachable = False
            new_status.online = False
            new_status.error = None
            if docker_running:
                new_status.offline_reason = f"container is up but hasn't responded yet -- probably still starting up ({e})"
            else:
                new_status.offline_reason = None

        async with self._lock:
            self._status = new_status

    async def _loop(self) -> None:
        while True:
            try:
                await self._refresh_once()
            except Exception as e:
                log.exception("status refresh failed for %s: %s", self._backend.slug, e)
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
