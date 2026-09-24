import json
import os
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_EVENT_NAME_RE = re.compile(r'STORM_NAME="([^"]*)"')
_EVENT_BLURB_RE = re.compile(r'STORM_BLURB="([^"]*)"')
_TAG_RE = re.compile(r"<[^>]*>")

EVENT_TZ = ZoneInfo("America/Toronto")
START_GRACE_MIN = 25

VACATION_EVENT = "storm-vacationday.sh"


def _dir(events_dir: str | None = None) -> str:
    return events_dir or os.environ.get("EVENTS_DIR", "/data/pz-storms")


_OVERRIDE_FILENAME = "event-override.json"


def _override_path(override_dir: str | None = None) -> str:
    base = override_dir or os.environ.get("CONTENT_OVERRIDE_DIR", "/data/content")
    return os.path.join(base, _OVERRIDE_FILENAME)


def mark_allow_tonight_override(script: str, override_dir: str | None = None) -> None:
    path = _override_path(override_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"script": script, "set_at": int(time.time())}, f)


def _read_override_script(override_dir: str | None = None) -> str | None:
    try:
        with open(_override_path(override_dir), "r", errors="replace") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data.get("script") if isinstance(data, dict) else None


def _read_script(script_basename: str, events_dir: str | None = None) -> str | None:
    path = os.path.join(_dir(events_dir), script_basename)
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _display_name(script_basename: str, events_dir: str | None = None) -> str | None:
    content = _read_script(script_basename, events_dir)
    if content is None:
        return None
    m = _EVENT_NAME_RE.search(content)
    return m.group(1) if m else None


def _flavor_text(script_basename: str, events_dir: str | None = None) -> str | None:
    content = _read_script(script_basename, events_dir)
    if content is None:
        return None
    m = _EVENT_BLURB_RE.search(content)
    if not m:
        return None
    segments = [s.strip() for s in _TAG_RE.split(m.group(1)) if s.strip()]
    return segments[0] if segments else None


def _last_start_date(events_dir: str | None = None) -> str | None:
    path = os.path.join(_dir(events_dir), ".last_storm_start_date")
    try:
        with open(path, "r", errors="replace") as f:
            return f.read().strip() or None
    except OSError:
        return None


def _iso_week_id(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def _week_days(events_dir: str | None = None) -> tuple[str, list[str]] | None:
    path = os.path.join(_dir(events_dir), ".storm_days")
    try:
        with open(path, "r", errors="replace") as f:
            parts = f.read().split()
    except OSError:
        return None
    if len(parts) < 2:
        return None
    return parts[0], parts[1:]


def _window_for_day(abbr: str) -> int:
    if abbr == "Sat":
        return 10
    if abbr == "Sun":
        return 12
    return 16


def _simple_start_display(start_epoch: int) -> str:
    dt = datetime.fromtimestamp(start_epoch, tz=EVENT_TZ)
    now = datetime.fromtimestamp(time.time(), tz=EVENT_TZ)
    hour12 = dt.strftime("%I").lstrip("0") or "12"
    ampm = dt.strftime("%p").lower()
    time_part = f"{hour12}:{dt.minute:02d}{ampm}" if dt.minute else f"{hour12}{ampm}"

    days_ahead = (dt.date() - now.date()).days
    if days_ahead == 0:
        day_part = "Tonight"
    elif days_ahead < 7:
        day_part = f"This {dt.strftime('%A')}"
    else:
        day_part = f"Next {dt.strftime('%A')}"
    return f"{day_part} at {time_part}"


def _next_start_epoch(now_epoch: int, events_dir: str | None = None) -> int:
    now = datetime.fromtimestamp(now_epoch, tz=EVENT_TZ)
    today_str = now.strftime("%Y-%m-%d")
    last_start = _last_start_date(events_dir)

    wk = _week_days(events_dir)
    if wk is not None:
        week_id, days = wk
        if week_id == _iso_week_id(now):
            for offset in range(0, 7):
                cand_date = now + timedelta(days=offset)
                if _iso_week_id(cand_date) != week_id:
                    break
                abbr = cand_date.strftime("%a")
                if abbr not in days:
                    continue
                if offset == 0 and last_start == today_str:
                    continue
                candidate = cand_date.replace(
                    hour=_window_for_day(abbr), minute=0, second=0, microsecond=0
                )
                if offset == 0 and candidate < now - timedelta(minutes=START_GRACE_MIN):
                    continue
                return int(candidate.timestamp())

    candidate = now.replace(hour=_window_for_day(now.strftime("%a")), minute=0, second=0, microsecond=0)
    today_already_used = last_start == today_str
    if today_already_used or candidate < now - timedelta(minutes=START_GRACE_MIN):
        candidate += timedelta(days=1)
        candidate = candidate.replace(hour=_window_for_day(candidate.strftime("%a")))
    return int(candidate.timestamp())


def read_active(events_dir: str | None = None) -> dict | None:
    path = os.path.join(_dir(events_dir), ".active_storm")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", errors="replace") as f:
            parts = f.read().split()
    except OSError:
        return None
    if len(parts) != 2:
        return None
    script, end_str = parts
    try:
        end_epoch = int(end_str)
    except ValueError:
        return None

    return {
        "name": _display_name(script, events_dir) or script,
        "seconds_left": max(0, end_epoch - int(time.time())),
        "flavor": _flavor_text(script, events_dir),
    }


def read_next(events_dir: str | None = None, override_dir: str | None = None) -> dict | None:
    path = os.path.join(_dir(events_dir), ".storm_queue")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", errors="replace") as f:
            queue = f.read().split()
    except OSError:
        return None
    if not queue:
        return None

    script = queue[0]
    name = _display_name(script, events_dir)
    start_epoch = _next_start_epoch(int(time.time()), events_dir)
    start_display = datetime.fromtimestamp(start_epoch, tz=EVENT_TZ).strftime("%b %-d, %Y %H:%M %Z")
    return {
        "name": name or f"{script} (script missing)",
        "flavor": _flavor_text(script, events_dir),
        "script": script,
        "start_epoch": start_epoch,
        "start_display": start_display,
        "start_display_simple": _simple_start_display(start_epoch),
        "overridden_early": _read_override_script(override_dir) == script,
    }
