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


def read_positions(online_names: set[str]) -> dict:
    latest: dict[str, tuple[int, int, float]] = {}

    path = game_logs.find_current("cmd")
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

    now = time.time()
    players = [
        {
            "name": name, "x": x, "y": y,
            "seconds_ago": max(0, int(now - ts)),
            "on_map": _in_world_bounds(x, y),
        }
        for name, (x, y, ts) in latest.items()
    ]
    return {
        "origin_x": MAP_ORIGIN_X,
        "origin_y": MAP_ORIGIN_Y,
        "image_scale": MAP_IMAGE_SCALE,
        "image_w": MAP_IMAGE_W,
        "image_h": MAP_IMAGE_H,
        "players": players,
    }
