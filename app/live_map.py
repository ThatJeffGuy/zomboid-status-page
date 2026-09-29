import json
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app import game_logs

_LOG_TZ = ZoneInfo("America/Toronto")

_CMD_LINE_RE = re.compile(
    r'^\[(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+\]\s+\d+(?:\([^)]*\))?\s+'
    r'"([^"]*)"\s+\S+\s+@\s+(-?\d+),(-?\d+),(-?\d+)\.$'
)

_TAIL_BYTES = 512 * 1024

# The user log's join lines. While someone is connecting (joined, not yet "fully connected") or before
# their first position of this session, their dot goes in the Off Map box instead of wherever they
# stood last time (the user, 2026-09-29).
_USER_LINE_RE = re.compile(
    r'^\[(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+\]\s+\d+(?:\([^)]*\))?\s+'
    r'"([^"]*)"\s+(attempting to join|fully connected \((-?\d+),(-?\d+),(-?\d+)\))'
)


def _log_ts(dd, mm, yy, hh, mi, ss) -> float:
    return datetime(2000 + int(yy), int(mm), int(dd), int(hh), int(mi), int(ss), tzinfo=_LOG_TZ).timestamp()


def _join_states(logs_dir: str | None) -> dict[str, dict]:
    """name -> {"join": ts of the last join attempt, "conn": ts of the last full connect, "x", "y"}."""
    states: dict[str, dict] = {}
    path = game_logs.find_current("user", logs_dir)
    if path is None:
        return states
    for line in _tail_lines(path, _TAIL_BYTES):
        m = _USER_LINE_RE.match(line.rstrip("\n"))
        if not m:
            continue
        dd, mm, yy, hh, mi, ss, name, what, x, y, _z = m.groups()
        st = states.setdefault(name, {})
        ts = _log_ts(dd, mm, yy, hh, mi, ss)
        if what.startswith("attempting"):
            st["join"] = ts
        else:
            st["conn"], st["x"], st["y"] = ts, int(x), int(y)
    return states


def _tail_lines(path: str, max_bytes: int) -> list[str]:
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                f.readline()
            data = f.read()
    except OSError:
        return []
    return data.decode("utf-8", "replace").splitlines()


MAP_ORIGIN_X = 321
MAP_ORIGIN_Y = 384
MAP_IMAGE_SCALE = 11.67
MAP_IMAGE_W = 1400
MAP_IMAGE_H = 1386

_WORLD_MARGIN = 1500
_WORLD_X_MIN = MAP_ORIGIN_X - _WORLD_MARGIN
_WORLD_X_MAX = MAP_ORIGIN_X + MAP_IMAGE_W * MAP_IMAGE_SCALE + _WORLD_MARGIN
_WORLD_Y_MIN = MAP_ORIGIN_Y - _WORLD_MARGIN
_WORLD_Y_MAX = MAP_ORIGIN_Y + MAP_IMAGE_H * MAP_IMAGE_SCALE + _WORLD_MARGIN


def _in_world_bounds(x: int, y: int) -> bool:
    return _WORLD_X_MIN <= x <= _WORLD_X_MAX and _WORLD_Y_MIN <= y <= _WORLD_Y_MAX


_SAFEZONE_MAX_AGE = 3 * 86400   # the server pauses while empty, so the file can be old; falls_at is absolute


def read_safe_zone(path: str | None) -> dict | None:
    """The shrinking safe zone written by the game server (PE_SafePath.lua), if fresh."""
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or time.time() - float(data.get("updated") or 0) > _SAFEZONE_MAX_AGE:
        return None
    return data


def read_positions(online_names: set[str], logs_dir: str | None = None, safezone_file: str | None = None) -> dict:
    latest: dict[str, tuple[int, int, float]] = {}

    path = game_logs.find_current("cmd", logs_dir)
    if path is not None:
        lines = _tail_lines(path, _TAIL_BYTES)

        for line in lines:
            m = _CMD_LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            dd, mm, yy, hh, mi, ss, name, x_s, y_s, _z_s = m.groups()
            if name not in online_names:
                continue
            x, y = int(x_s), int(y_s)
            year = 2000 + int(yy)
            ts = datetime(year, int(mm), int(dd), int(hh), int(mi), int(ss), tzinfo=_LOG_TZ).timestamp()
            latest[name] = (x, y, ts)

    # connecting, or no position yet this session: the Off Map box
    joins = _join_states(logs_dir)
    connecting: set[str] = set()
    for name in online_names:
        st = joins.get(name, {})
        conn, join = st.get("conn"), st.get("join")
        if join is not None and (conn is None or join > conn):
            connecting.add(name)
            latest.pop(name, None)
        elif conn is not None and (name not in latest or latest[name][2] < conn):
            latest[name] = (st["x"], st["y"], conn)        # the spot they spawned in at, until they move
    now = time.time()
    players = [
        {
            "name": name, "x": x, "y": y,
            "seconds_ago": max(0, int(now - ts)),
            "on_map": _in_world_bounds(x, y),
        }
        for name, (x, y, ts) in latest.items()
    ]
    for name in sorted(online_names):
        if name not in latest:
            players.append({"name": name, "x": None, "y": None, "seconds_ago": None, "on_map": False,
                            "connecting": name in connecting})
    return {
        "origin_x": MAP_ORIGIN_X,
        "origin_y": MAP_ORIGIN_Y,
        "image_scale": MAP_IMAGE_SCALE,
        "image_w": MAP_IMAGE_W,
        "image_h": MAP_IMAGE_H,
        "players": players,
        "safe_zone": read_safe_zone(safezone_file),
    }
